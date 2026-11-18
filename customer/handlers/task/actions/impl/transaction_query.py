"""查询账户交易流水 Action."""
import logging
from customer.clients.finance_client import finance_client
from customer.domain.state import DialogueState
from customer.handlers.task.actions.base import Action, ActionResult

logger = logging.getLogger(__name__)


class TransactionQueryAction(Action):
    """查询账户历史交易明细."""

    name = "action_query_transactions"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.tasks.active.slots if state.tasks.active else {}
        account_no = slots.get("account_no")
        start_date = slots.get("start_date") or slots.get("date")
        end_date = slots.get("end_date")

        if not account_no:
            return ActionResult(
                success=False,
                error="缺少账户号",
                result={"reply": "请提供需要查询交易明细的银行卡号或账户号。"}
            )

        try:
            data = await finance_client.get_transactions(
                account_no=str(account_no),
                start_date=start_date,
                end_date=end_date,
            )
            items = data.get("items", []) if isinstance(data, dict) else []
            count = len(items)

            return ActionResult(
                success=True,
                result={
                    "account_no": account_no,
                    "count": count,
                    "transactions": items[:5],
                    "reply": f"已为您查询到账户 {account_no} 的最近 {count} 笔交易记录。"
                }
            )
        except Exception as e:
            logger.error("查询交易流水失败: %s", e)
            return ActionResult(
                success=False,
                error=str(e),
                result={"reply": f"查询交易明细失败，请稍后重试。({e})"}
            )
