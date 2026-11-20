"""创建客服投诉工单 Action."""
import logging

from customer.actions.base import (
    Action,
    ActionResult,
    format_action_error,
    get_active_slots,
    resolve_customer_no,
)
from customer.clients.finance_client import finance_client
from customer.domain.state import DialogueState

logger = logging.getLogger(__name__)


class ComplaintTicketAction(Action):
    """创建客户投诉或咨询工单."""

    name = "action_create_complaint_ticket"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = get_active_slots(state)
        is_handoff = bool(state.tasks.active and state.tasks.active.flow_id == "human_handoff")
        customer_no = resolve_customer_no(state, slots) or finance_client.default_customer_no
        category = (
            slots.get("ticket_category")
            or slots.get("complaint_category")
            or slots.get("ticket_type")
            or slots.get("category")
            or ("人工专席跟进" if is_handoff else "服务投诉")
        )
        description = (
            slots.get("ticket_description")
            or slots.get("complaint_description")
            or slots.get("description")
            or slots.get("problem_desc")
        )
        if not description and is_handoff:
            recent_texts: list[str] = []
            if state.shared.sessions:
                for turn in state.shared.sessions[-1].turns[-3:]:
                    if turn.user_message and turn.user_message.text:
                        recent_texts.append(turn.user_message.text.strip())
            summary = "；".join(t for t in recent_texts if t)
            description = (
                f"客户请求转接人工客服专员协助处理（最近上下文：{summary[:200]}）"
                if summary
                else "客户请求转接人工客服专员协助处理。"
            )
        related_no = slots.get("related_no") or slots.get("transaction_no")

        if not description:
            return ActionResult(
                result={"reply": "请详细描述您遇到的问题经过或投诉诉求，以便为您登记工单。"}
            )

        try:
            data = await finance_client.create_support_ticket(
                customer_no=customer_no,
                category=str(category),
                description=str(description),
                related_no=str(related_no) if related_no else None,
            )
            ticket_no = data.get("ticket_no", "")
            ticket_status = data.get("ticket_status", "submitted")

            reply_text = (
                f"好的，已为您登记人工客服专席跟进单【{ticket_no}】，专席人员查看上下文后将尽快在对话窗或消息中心向您反馈处理结果。"
                if is_handoff
                else (
                    f"您的投诉工单已创建成功！工单编号为【{ticket_no}】（问题类型：{category}），"
                    "我们已安排专席客服进行跟进核实，将在 24 小时内向您反馈处理进展。"
                )
            )
            return ActionResult(
                result={
                    "ticket_no": ticket_no,
                    "ticket_status": ticket_status,
                    "ticket_category": category,
                    "reply": reply_text,
                },
                receipt={
                    "kind": "ticket",
                    "title": "人工跟进回执" if is_handoff else "工单回执",
                    "sealText": "已登记",
                    "ticketNo": str(ticket_no),
                    "category": str(category),
                },
            )
        except Exception as e:
            logger.error("创建投诉工单失败: %s", e)
            if is_handoff:
                return ActionResult(
                    result={"reply": "好的，已为您转接银行人工客服专员，请稍候。"}
                )
            return ActionResult(
                result={"reply": f"创建工单失败：{format_action_error(e)}，请稍后重试或联系人工客服。"}
            )
