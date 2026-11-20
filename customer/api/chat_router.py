"""
创建路由
"""
import asyncio
import json
import uuid
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse

from customer.api.dependencies import get_dialogue_service
from customer.api.schemas import (
    AdminTicketHandleRequest,
    ChatMessage,
    ChatObject,
    ChatRequest,
    ChatResponse,
    CustomerAssetsResponse,
    CustomerTicketFeedbackRequest,
    HistoryMessage,
    HistoryResponse,
    RagStatusResponse,
    SessionTokenRequest,
    SessionTokenResponse,
)
from customer.clients.finance_client import finance_client
from customer.clients.rag_client import rag_client
from customer.config.config import settings
from customer.domain.messages import MessageObject, MessageType, ProcessResult, UserMessage
from customer.domain.state import DialogueState, Session, Turn
from customer.engine.protocol import build_workflow_snapshot
from customer.security.auth import issue_session_token, validate_sender_authorization
from customer.security.masking import mask_identifier
from customer.service.dialogue_service import DialogueService

chat_router = APIRouter()


def _format_sse(event_name: str, data: dict[str, Any] | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event_name}\ndata: {payload}\n\n"


@chat_router.post("/api/auth/session", response_model=SessionTokenResponse)
async def create_session_token(req: SessionTokenRequest) -> SessionTokenResponse:
    """签发客户会话签名凭证（HS256）."""
    issued = issue_session_token(req.customer_no)
    return SessionTokenResponse(**issued)


@chat_router.post("/api/chat")
async def chat(
    chat_request: ChatRequest,
    dialogue_service: DialogueService = Depends(get_dialogue_service),
    authorization: str | None = Header(default=None),
) -> ChatResponse:
    validate_sender_authorization(chat_request.sender_id, authorization)
    user_message: UserMessage = _build_user_message(chat_request)
    process_result: ProcessResult = await dialogue_service.run(user_message)
    return _build_response_message(process_result)


@chat_router.post("/api/chat/stream")
async def chat_stream(
    chat_request: ChatRequest,
    dialogue_service: DialogueService = Depends(get_dialogue_service),
    authorization: str | None = Header(default=None),
) -> StreamingResponse:
    """SSE 流式对话接口：实时推送处理阶段、文本增量与最终结构化结果."""
    validate_sender_authorization(chat_request.sender_id, authorization)
    user_message: UserMessage = _build_user_message(chat_request)

    async def event_stream():
        queue: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue()

        async def on_stage(stage: str, label: str) -> None:
            await queue.put(("stage", {"stage": stage, "label": label}))

        async def run_turn() -> ProcessResult:
            try:
                return await dialogue_service.run(user_message, on_stage=on_stage)
            finally:
                await queue.put(None)

        worker = asyncio.create_task(run_turn())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                event_name, payload = item
                yield _format_sse(event_name, payload)

            process_result = await worker
            chat_response = _build_response_message(process_result)

            # 对最后一条主回复按小片段流式推送，保证打字机体感且与脱敏/落库完全一致
            stream_target = next(
                (msg for msg in reversed(chat_response.messages) if msg.text and msg.event is None),
                None,
            )
            if stream_target and stream_target.text:
                text = stream_target.text
                chunk_size = 10
                for start in range(0, len(text), chunk_size):
                    yield _format_sse("delta", {"text": text[start : start + chunk_size]})
                    await asyncio.sleep(0.01)

            yield _format_sse("done", chat_response.model_dump_json())
        except Exception as exc:
            yield _format_sse("error", {"message": str(exc) or "智能客服处理失败，请稍后重试"})
        finally:
            if not worker.done():
                worker.cancel()
                await asyncio.gather(worker, return_exceptions=True)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# 调用service方法，把api层数据模型 转换 service层数据模型
    # ChatRequest -->  UserMessage
def _build_user_message(chat_request:ChatRequest)->UserMessage:
    return UserMessage(
        sender_id=chat_request.sender_id,
        # 消息id，判断存在使用，不存在生成
        message_id=chat_request.message_id
               if chat_request.message_id else str(uuid.uuid4()),
        type=MessageType.TEXT if chat_request.text
                              else MessageType.OBJECT,
        text=chat_request.text,
        object=MessageObject(
            id=chat_request.object.id,
            type=chat_request.object.type,
            title=chat_request.object.title,
            attributes=chat_request.object.attributes,
        ) if chat_request.object else None
    )


# 3 把service层返回数据 ProcessResult --> api层类型 ChatResponse
# ProcessResult -->  ChatResponse
def _build_response_message(process_result:ProcessResult)->ChatResponse:
    # list[BotMessage] --》 list[ChatMessage]
    return ChatResponse(
        sender_id=process_result.sender_id,
        message_id=process_result.message_id,
        messages=[
            # ChatMessage对象
            ChatMessage(
                text=bot_message.text,
                object=ChatObject(
                    **asdict(bot_message.object)
                ) if bot_message.object else None,
                receipt=bot_message.receipt,
                event=bot_message.event,
                citations=bot_message.citations,
            )
            for bot_message in process_result.messages
        ],
        workflow_state=process_result.workflow_state,
        quick_replies=process_result.quick_replies,
    )

# 接口：根据当前用户id查询用户历史会话记录
@chat_router.get("/api/chat/history")
async def chat_history(
    sender_id: str,
    dialogue_service: DialogueService = Depends(get_dialogue_service),
    authorization: str | None = Header(default=None),
) -> HistoryResponse:
    validate_sender_authorization(sender_id, authorization)
    history_data: DialogueState = await dialogue_service.get_history_data_sender_id(sender_id)
    sessions: list[Session] = history_data.shared.sessions

    messages: list[HistoryMessage] = []
    for session in sessions:
        turns: list[Turn] = session.turns
        for turn in turns:
            if turn.user_message and (turn.user_message.text or turn.user_message.object):
                messages.append(
                    HistoryMessage(
                        role="user",
                        text=turn.user_message.text,
                        object=ChatObject(**asdict(turn.user_message.object))
                        if turn.user_message.object
                        else None,
                    )
                )
            messages.extend(
                [
                    HistoryMessage(
                        role="bot",
                        text=bot_message.text,
                        object=None,
                        receipt=bot_message.receipt,
                        event=bot_message.event,
                        citations=bot_message.citations,
                    )
                    for bot_message in turn.bot_message
                ]
            )

    flow_catalog = dialogue_service.engine._get_flow_catalog()
    workflow_state, quick_replies = build_workflow_snapshot(history_data, flow_catalog)

    return HistoryResponse(
        sender_id=sender_id,
        messages=messages,
        workflow_state=workflow_state,
        quick_replies=quick_replies,
    )


@chat_router.get("/api/customer/assets", response_model=CustomerAssetsResponse)
async def customer_assets(
    sender_id: str,
    authorization: str | None = Header(default=None),
) -> CustomerAssetsResponse:
    """汇总拉取中台客户真实账户余额、授信额度与理财持仓（实时脱敏）."""
    validate_sender_authorization(sender_id, authorization)
    accounts_res, limits_res, wealth_res, profile_res = await asyncio.gather(
        finance_client.get_customer_accounts(customer_no=sender_id),
        finance_client.get_credit_limits(customer_no=sender_id),
        finance_client.get_customer_wealth_positions(customer_no=sender_id),
        finance_client.get_customer_profile(customer_no=sender_id),
        return_exceptions=True,
    )

    accounts: list[dict[str, Any]] = []
    if isinstance(accounts_res, list):
        for acc in accounts_res:
            account_no = str(acc.get("account_no") or "")
            accounts.append(
                {
                    "account_no": account_no,
                    "masked_account_no": mask_identifier(account_no),
                    "balance_amount": str(acc.get("balance_amount") or "0.00"),
                    "currency_code": str(acc.get("currency_code") or "CNY"),
                    "account_product": acc.get("account_product") or {},
                }
            )

    credit_limits: list[dict[str, Any]] = limits_res if isinstance(limits_res, list) else []
    wealth_positions: list[dict[str, Any]] = wealth_res if isinstance(wealth_res, list) else []

    customer_name: str | None = None
    risk_level: dict[str, Any] | None = None
    if isinstance(profile_res, dict):
        customer_profile = profile_res.get("customer_profile") or {}
        if isinstance(customer_profile, dict):
            customer_name = customer_profile.get("customer_name")
        risk_level = profile_res.get("risk_level")

    synced = any(
        not isinstance(item, Exception)
        for item in (accounts_res, limits_res, wealth_res, profile_res)
    )
    return CustomerAssetsResponse(
        customer_no=sender_id,
        customer_name=customer_name,
        risk_level=risk_level,
        accounts=accounts,
        credit_limits=credit_limits,
        wealth_positions=wealth_positions,
        synced=synced,
    )


@chat_router.get("/api/rag/status", response_model=RagStatusResponse)
async def rag_status() -> RagStatusResponse:
    """探测金融智脑 (finance_brain) 问答服务与文档导入服务状态及工作台地址."""
    health = (
        await rag_client.check_health()
        if settings.rag_enabled
        else {"query_online": False, "import_online": False}
    )
    query_base = rag_client.base_url
    import_base = rag_client.import_base_url
    return RagStatusResponse(
        enabled=settings.rag_enabled,
        query_online=health["query_online"],
        import_online=health["import_online"],
        query_url=query_base,
        chat_url=f"{query_base}/chat.html",
        import_url=f"{import_base}/import.html",
    )


@chat_router.get("/api/admin/tickets")
async def admin_list_tickets(
    ticket_status: str | None = None,
    customer_no: str | None = None,
    keyword: str | None = None,
    page_no: int = 1,
    page_size: int = 20,
    operator_no: str | None = None,
) -> dict[str, Any]:
    """员工工单管理台：分页查询客户投诉/反馈/人工跟进工单列表."""
    try:
        return await finance_client.list_support_tickets(
            ticket_status=ticket_status,
            customer_no=customer_no,
            keyword=keyword,
            page_no=page_no,
            page_size=page_size,
            operator_no=operator_no,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"拉取中台工单列表失败: {exc}") from exc


@chat_router.get("/api/admin/tickets/{ticket_no}")
async def admin_get_ticket(ticket_no: str) -> dict[str, Any]:
    """员工工单管理台：查询单张工单详情."""
    try:
        return await finance_client.get_support_ticket(ticket_no=ticket_no)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"查询中台工单详情失败: {exc}") from exc


@chat_router.post("/api/admin/tickets/{ticket_no}/handle")
async def admin_handle_ticket(
    ticket_no: str,
    body: AdminTicketHandleRequest,
    dialogue_service: DialogueService = Depends(get_dialogue_service),
) -> dict[str, Any]:
    """员工工单管理台：提交处理结果并实时向客户对话窗反馈进度."""
    try:
        handled = await finance_client.handle_support_ticket(
            ticket_no=ticket_no,
            ticket_status=body.ticket_status,
            handle_result=body.handle_result,
            operator_no=body.operator_no,
            notify_customer=body.notify_customer,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"提交中台工单处理失败: {exc}") from exc

    push_result: dict[str, Any] | None = None
    customer_info = handled.get("customer") or {}
    customer_no = str(customer_info.get("customer_no") or "").strip()
    if body.push_to_chat and customer_no:
        push_result = await dialogue_service.push_ticket_feedback_to_customer(
            customer_no=customer_no,
            ticket_data=handled,
        )

    return {
        **handled,
        "chat_push": push_result,
    }


@chat_router.post("/api/customer/tickets/{ticket_no}/feedback")
async def customer_submit_ticket_feedback(
    ticket_no: str,
    body: CustomerTicketFeedbackRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """客户对专席工单处理结果提交确认与满意度评价."""
    validate_sender_authorization(body.customer_no, authorization)
    try:
        return await finance_client.submit_ticket_feedback(
            ticket_no=ticket_no,
            customer_no=body.customer_no,
            confirm_status=body.confirm_status,
            satisfaction_score=body.satisfaction_score,
            feedback_content=body.feedback_content,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"提交工单确认评价失败: {exc}") from exc