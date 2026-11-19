"""信用卡/账户紧急挂失 Action."""
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


class CardLossAction(Action):
    """信用卡/银行卡紧急挂失."""

    name = "action_report_card_loss"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = get_active_slots(state)
        raw_card_no = slots.get("card_no") or slots.get("account_no")
        loss_reason = slots.get("loss_reason") or slots.get("reason") or "客户紧急口头挂失"
        customer_no = resolve_customer_no(state, slots)

        if not raw_card_no:
            return ActionResult(
                result={"reply": "请提供需要挂失的银行卡号或信用卡号。"}
            )

        normalized_no = normalize_identifier(raw_card_no)
        try:
            data = await finance_client.change_account_status(
                account_no=normalized_no,
                target_status="loss_reported",
                reason=str(loss_reason),
                customer_no=customer_no,
            )
            current_status = data.get("current_status", "loss_reported")
            resolved_account = str(data.get("account_no") or normalized_no)
            return ActionResult(
                result={
                    "card_no": normalized_no,
                    "resolved_account_no": resolved_account,
                    "status": current_status,
                    "status_history_id": data.get("status_history_id"),
                    "reply": (
                        f"您的卡片/账户【{normalized_no}】已成功办理紧急挂失（状态：{current_status}），资金安全已受保护。"
                        "如需解挂或补办新卡，请携带有效身份证件前往网点或在手机银行办理。"
                    ),
                }
            )
        except Exception as e:
            logger.error("卡片挂失操作失败: %s", e)
            return ActionResult(
                result={"reply": f"挂失操作失败：{format_action_error(e)}，请立即拨打我行 24 小时人工客服电话 95555 进行紧急止付。"}
            )
