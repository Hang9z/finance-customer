"""信用卡/账户挂失 Action."""
import logging
from customer.clients.finance_client import finance_client
from customer.domain.state import DialogueState
from customer.handlers.task.actions.base import Action, ActionResult

logger = logging.getLogger(__name__)


class CardLossAction(Action):
    """信用卡/银行卡紧急挂失."""

    name = "action_report_card_loss"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.tasks.active.slots if state.tasks.active else {}
        card_no = slots.get("card_no") or slots.get("account_no")
        reason = slots.get("reason") or slots.get("loss_reason") or "客户紧急口头挂失"

        if not card_no:
            return ActionResult(
                success=False,
                error="缺少卡号",
                result={"reply": "请提供需要挂失的银行卡号或信用卡号。"}
            )

        try:
            data = await finance_client.change_account_status(
                account_no=str(card_no),
                target_status="frozen",
                reason=reason,
            )
            return ActionResult(
                success=True,
                result={
                    "card_no": card_no,
                    "status": "frozen",
                    "reply": f"您的卡片【{card_no}】已成功办理紧急挂失并冻结账户，资金安全已受保护。如需补办新卡，请携带有效身份证件前往任意网点或在手机银行办理。"
                }
            )
        except Exception as e:
            logger.error("卡片挂失操作失败: %s", e)
            return ActionResult(
                success=False,
                error=str(e),
                result={"reply": f"挂失操作失败，请立即拨打我行 24 小时人工客服电话 95555 进行紧急止付。({e})"}
            )
