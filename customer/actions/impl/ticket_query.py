"""查询客服投诉工单处理进度 Action."""
import logging

from customer.actions.base import (
    Action,
    ActionResult,
    format_action_error,
    get_active_slots,
    normalize_identifier,
    resolve_customer_no,
)
from customer.clients.finance_client import finance_client
from customer.domain.state import DialogueState

logger = logging.getLogger(__name__)

_TICKET_STATUS_LABELS = {
    "submitted": "已受理待处理",
    "processing": "处理中",
    "resolved": "已解决",
    "closed": "已完结",
    "cancelled": "已取消",
}


class TicketQueryAction(Action):
    """查询客服工单处理状态与专席进展."""

    name = "action_query_complaint_ticket"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = get_active_slots(state)
        raw_ticket_no = slots.get("ticket_no") or slots.get("related_no")
        customer_no = resolve_customer_no(state, slots)

        if not raw_ticket_no:
            return ActionResult(
                result={"reply": "请提供您需要查询进度的工单编号（例如 TKT 或 TCK 开头的编号）。"}
            )

        normalized_no = normalize_identifier(raw_ticket_no)
        try:
            data = await finance_client.get_support_ticket(
                ticket_no=normalized_no,
                customer_no=customer_no,
            )
            info = data.get("ticket_info") or {}
            handler = data.get("handler") or {}
            process_result = str(data.get("process_result") or info.get("handle_result") or "").strip()

            resolved_ticket_no = str(info.get("ticket_no") or normalized_no)
            ticket_type = str(info.get("ticket_type") or "客服工单")
            raw_status = str(info.get("ticket_status") or "submitted")
            status_text = _TICKET_STATUS_LABELS.get(raw_status, raw_status)
            handler_name = str(handler.get("employee_name") or handler.get("employee_no") or "专席客服")
            submitted_at = str(info.get("submitted_at") or "-")

            reply = (
                f"工单编号【{resolved_ticket_no}】（问题类型：{ticket_type}）当前处理状态为【{status_text}】，"
                f"负责专席：{handler_name}，提交时间：{submitted_at}。"
            )
            if process_result:
                reply = f"{reply}处理结果：{process_result}。"

            return ActionResult(
                result={
                    "ticket_no": resolved_ticket_no,
                    "ticket_category": ticket_type,
                    "ticket_status": raw_status,
                    "reply": reply,
                },
                receipt={
                    "kind": "ticket_progress",
                    "title": "工单进度回执",
                    "sealText": "已核验",
                    "ticketNo": resolved_ticket_no,
                    "category": ticket_type,
                    "status": status_text,
                    "handlerName": handler_name,
                    "processResult": process_result,
                    "submittedAt": submitted_at,
                    "handledAt": str(info.get("handled_at") or info.get("closed_at") or ""),
                },
            )
        except Exception as e:
            logger.error("查询工单进度失败: %s", e)
            return ActionResult(
                result={"reply": f"查询工单进度失败：{format_action_error(e)}，请核对工单编号是否正确或联系人工客服。"}
            )
