"""查询银行账户余额 Action."""
import logging
from customer.clients.finance_client import finance_client
from customer.domain.state import DialogueState
from customer.actions.base import Action, ActionResult

logger = logging.getLogger(__name__)


class AccountBalanceQueryAction(Action):
    """查询银行账户余额与状态."""

    name = "action_query_account_balance"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.tasks.active.slots if state.tasks.active else {}
        account_no = slots.get("account_no")
        customer_no = slots.get("customer_no")

        if not account_no:
            return ActionResult(
                result={"reply": "未获取到需要查询的银行卡号或账户号。"}
            )

        try:
            data = await finance_client.get_account(account_no=str(account_no), customer_no=customer_no)
            balance = data.get("balance", "0.00")
            available_balance = data.get("available_balance", balance)
            frozen_amount = data.get("frozen_amount", "0.00")
            currency = data.get("currency_code", "CNY")
            status = data.get("account_status", "active")

            return ActionResult(
                result={
                    "account_no": account_no,
                    "balance": balance,
                    "available_balance": available_balance,
                    "frozen_amount": frozen_amount,
                    "currency": currency,
                    "status": status,
                    "reply": f"您的账户 {account_no} 当前可用余额为 {available_balance} {currency}，冻结金额为 {frozen_amount} {currency}，账户状态正常。"
                }
            )
        except Exception as e:
            logger.error("查询账户余额失败: %s", e)
            return ActionResult(
                result={"reply": f"查询账户余额失败，请稍后重试或核对账号是否正确。({e})"}
            )
