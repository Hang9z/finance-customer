"""查询银行账户余额 Action."""
from decimal import Decimal
import logging

from customer.actions.base import Action, ActionResult, get_active_slots, resolve_customer_no
from customer.clients.finance_client import finance_client
from customer.domain.state import DialogueState

logger = logging.getLogger(__name__)

_STATUS_LABELS = {
    "normal": "正常",
    "active": "正常",
    "frozen": "已冻结",
    "loss_reported": "已挂失",
    "closed": "已销户",
}


class AccountBalanceQueryAction(Action):
    """查询银行账户余额与状态."""

    name = "action_query_account_balance"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = get_active_slots(state)
        account_no = slots.get("account_no") or slots.get("card_no")
        customer_no = resolve_customer_no(state, slots)

        if not account_no:
            return ActionResult(
                result={"reply": "未获取到需要查询的银行卡号或账户号。"}
            )

        try:
            data = await finance_client.get_account(account_no=str(account_no), customer_no=customer_no)
            balance = data.get("balance_amount") or data.get("balance", "0.00")
            frozen_amount = data.get("frozen_amount", "0.00")
            available_balance = data.get("available_balance") or data.get("available_amount")
            if available_balance is None:
                available_balance = f"{max(Decimal(str(balance)) - Decimal(str(frozen_amount)), Decimal('0.00')):.2f}"
            currency = data.get("currency_code", "CNY")
            status = data.get("account_status", "active")
            status_text = _STATUS_LABELS.get(status, status)

            return ActionResult(
                result={
                    "account_no": account_no,
                    "balance": str(balance),
                    "available_balance": str(available_balance),
                    "frozen_amount": str(frozen_amount),
                    "currency": currency,
                    "status": status,
                    "reply": (
                        f"您的账户 {account_no} 当前可用余额为 {available_balance} {currency}，"
                        f"冻结金额为 {frozen_amount} {currency}，账户状态：{status_text}。"
                    ),
                }
            )
        except Exception as e:
            logger.error("查询账户余额失败: %s", e)
            return ActionResult(
                result={"reply": f"查询账户余额失败，请稍后重试或核对账号是否正确。({e})"}
            )
