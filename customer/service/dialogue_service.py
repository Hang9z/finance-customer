"""
这个模块是service业务逻辑层，负责调用其他层实现
调用repository操作数据库
调用engine处理消息
"""
from collections.abc import Awaitable, Callable
import time
import uuid
from typing import Any

from customer.domain.messages import BotMessage, MessageType, ProcessResult, UserMessage
from customer.domain.state import DialogueState, Session, Turn
from customer.engine.dialogue_engine import DialogueEngine
from customer.repository.dialogue_repository import DialogueRepository
from customer.security.masking import mask_sensitive_text


_TICKET_STATUS_ZH = {
    "submitted": "已受理待处理",
    "processing": "处理中",
    "resolved": "已解决",
    "closed": "已完结",
    "rejected": "已退回",
    "cancelled": "已取消",
}


class DialogueService:

    def __init__(self, repository: DialogueRepository, engine: DialogueEngine):
        self.repository = repository
        self.engine = engine

    async def run(
        self,
        user_message: UserMessage,
        on_stage: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> ProcessResult:
        # 1 注入要调用层对象，repository对象（操作数据库） 和 engine对象（处理消息）
        # 2 根据sender_id获取当前用户历史消息处理数据
        sender_id = user_message.sender_id
        # 调用repository层方法进行查询
        state:DialogueState = await self.repository.load_state(sender_id)

        # 3 调用engine层方法处理当前用户消息
        process_result:ProcessResult = await self.engine.process_message(state, user_message, on_stage=on_stage)

        # 4 把处理消息之后最新处理数据保存数据库里面
        await self.repository.save_state(state)

        # 5 返回engine处理结果
        return process_result

    async def get_history_data_sender_id(self, sender_id: str) -> DialogueState:
        """根据用户标识加载历史对话状态."""
        return await self.repository.load_state(sender_id)

    async def push_ticket_feedback_to_customer(
        self,
        customer_no: str,
        ticket_data: dict[str, Any],
    ) -> dict[str, Any]:
        """将员工在后台处理的工单结果作为专席反馈消息实时写入客户对话流."""
        info = ticket_data.get("ticket_info") or {}
        handler = ticket_data.get("handler") or {}

        ticket_no = str(info.get("ticket_no") or "")
        ticket_type = str(info.get("ticket_type") or "客服工单")
        raw_status = str(info.get("ticket_status") or "resolved")
        status_label = _TICKET_STATUS_ZH.get(raw_status, raw_status)
        handler_name = str(
            handler.get("employee_name") or handler.get("employee_no") or "专席客服"
        )
        process_result = str(
            ticket_data.get("process_result") or info.get("handle_result") or ""
        ).strip()
        submitted_at = str(info.get("submitted_at") or "-")
        handled_at = str(info.get("handled_at") or info.get("closed_at") or "-")

        text = (
            f"【专席处理结果通知】您的工单【{ticket_no}】（问题类型：{ticket_type}）"
            f"状态已更新为【{status_label}】（经办专席：{handler_name}）。\n"
            f"处理说明：{mask_sensitive_text(process_result)}"
        )
        bot_msg = BotMessage(
            text=text,
            receipt={
                "kind": "ticket_progress",
                "title": "专席反馈凭证",
                "sealText": status_label,
                "ticketNo": ticket_no,
                "category": ticket_type,
                "status": status_label,
                "handlerName": handler_name,
                "processResult": mask_sensitive_text(process_result),
                "submittedAt": submitted_at,
                "handledAt": handled_at,
            },
        )

        state = await self.repository.load_state(customer_no)
        now = time.time()
        if not state.shared.sessions or state.shared.sessions[-1].closed_at is not None:
            state.shared.sessions.append(
                Session(
                    session_id=str(uuid.uuid4()),
                    started_at=now,
                    last_activity_at=now,
                )
            )
        else:
            state.shared.sessions[-1].last_activity_at = now

        turn = Turn(
            turn_id=str(uuid.uuid4()),
            user_message=UserMessage(
                sender_id=customer_no,
                message_id=f"staff_push_{uuid.uuid4().hex[:12]}",
                type=MessageType.TEXT,
                text="",
            ),
            bot_message=[bot_msg],
        )
        state.shared.sessions[-1].turns.append(turn)
        await self.repository.save_state(state)

        return {
            "customer_no": customer_no,
            "ticket_no": ticket_no,
            "status_label": status_label,
            "pushed": True,
        }