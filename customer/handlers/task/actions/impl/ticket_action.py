"""创建投诉工单 Action."""
import logging
from customer.clients.finance_client import finance_client
from customer.domain.state import DialogueState
from customer.handlers.task.actions.base import Action, ActionResult

logger = logging.getLogger(__name__)


class ComplaintTicketAction(Action):
    """创建客户投诉或咨询工单."""

    name = "action_create_complaint_ticket"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.tasks.active.slots if state.tasks.active else {}
        customer_no = slots.get("customer_no") or "CUST00000001"
        category = slots.get("ticket_type") or slots.get("category") or "服务投诉"
        description = slots.get("description") or slots.get("problem_desc") or "客户反映交易/服务问题"
        related_no = slots.get("transaction_no") or slots.get("related_no")

        try:
            data = await finance_client.create_support_ticket(
                customer_no=customer_no,
                category=category,
                description=description,
                related_no=related_no,
            )
            ticket_no = data.get("ticket_no", "TICK_TEMP_001")

            return ActionResult(
                success=True,
                result={
                    "ticket_no": ticket_no,
                    "category": category,
                    "reply": f"您的投诉工单已创建成功！工单编号为【{ticket_no}】，我们已安排专席客服进行跟进核实，将在 24 小时内向您反馈处理进展。"
                }
            )
        except Exception as e:
            logger.error("创建投诉工单失败: %s", e)
            return ActionResult(
                success=False,
                error=str(e),
                result={"reply": f"创建工单失败，请稍后重试。({e})"}
            )
