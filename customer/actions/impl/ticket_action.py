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
        customer_no = resolve_customer_no(state, slots) or finance_client.default_customer_no
        category = (
            slots.get("ticket_category")
            or slots.get("complaint_category")
            or slots.get("ticket_type")
            or slots.get("category")
            or "服务投诉"
        )
        description = (
            slots.get("ticket_description")
            or slots.get("complaint_description")
            or slots.get("description")
            or slots.get("problem_desc")
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

            return ActionResult(
                result={
                    "ticket_no": ticket_no,
                    "ticket_status": ticket_status,
                    "ticket_category": category,
                    "reply": (
                        f"您的投诉工单已创建成功！工单编号为【{ticket_no}】（问题类型：{category}），"
                        "我们已安排专席客服进行跟进核实，将在 24 小时内向您反馈处理进展。"
                    ),
                }
            )
        except Exception as e:
            logger.error("创建投诉工单失败: %s", e)
            return ActionResult(
                result={"reply": f"创建工单失败：{format_action_error(e)}，请稍后重试或联系人工客服。"}
            )
