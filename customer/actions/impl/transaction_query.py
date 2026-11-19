"""查询账户交易流水 Action."""
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
from customer.security.masking import mask_identifier

logger = logging.getLogger(__name__)

_CREDIT_TYPES = {
    "deposit",
    "refund",
    "loan_disbursement",
    "wealth_redeem",
    "income_settle",
    "adjustment_credit",
}

_TX_TYPE_LABELS = {
    "payment": "消费",
    "transfer": "转账",
    "wealth_purchase": "理财申购",
    "wealth_redeem": "理财赎回",
    "loan_repayment": "贷款还款",
    "loan_disbursement": "贷款放款",
    "deposit": "存入",
    "refund": "退款",
    "income_settle": "收益结算",
    "adjustment_credit": "调账入账",
    "adjustment_debit": "调账扣款",
    "fee": "手续费",
    "withdrawal": "取现",
}


def _build_tx_rows(items: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for tx in items[:5]:
        type_raw = str(tx.get("transaction_type") or "交易")
        rows.append(
            {
                "time": str(tx.get("transaction_at") or tx.get("created_at") or "-"),
                "typeRaw": type_raw,
                "typeLabel": _TX_TYPE_LABELS.get(type_raw, type_raw),
                "amount": str(tx.get("transaction_amount") or tx.get("amount") or "0.00"),
                "currency": str(tx.get("currency_code") or "CNY"),
                "isCredit": type_raw in _CREDIT_TYPES,
                "counterparty": str(tx.get("merchant_name") or tx.get("counterparty_name") or "-"),
                "status": str(tx.get("transaction_status") or "-"),
            }
        )
    return rows


def _format_transactions_reply(masked_account_no: str, items: list[dict], total_count: int) -> str:
    """将交易明细列表格式化为可读中文答复."""
    if not items:
        return f"账户 {masked_account_no} 在查询范围内暂无交易流水记录。"

    lines = [f"已为您查询到账户 {masked_account_no} 的近期交易记录（共 {total_count} 笔，以下展示最近 {min(len(items), 5)} 笔）："]
    for idx, tx in enumerate(items[:5], start=1):
        tx_time = tx.get("transaction_at") or tx.get("created_at") or "-"
        tx_type = tx.get("transaction_type") or "交易"
        amount = tx.get("transaction_amount") or tx.get("amount") or "0.00"
        currency = tx.get("currency_code") or "CNY"
        counterparty = tx.get("merchant_name") or tx.get("counterparty_name") or "-"
        status = tx.get("transaction_status") or "-"
        lines.append(f"{idx}. [{tx_time}] {tx_type} {amount} {currency} | 对象：{counterparty} | 状态：{status}")
    return "\n".join(lines)


class TransactionQueryAction(Action):
    """查询账户历史交易明细."""

    name = "action_query_transactions"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = get_active_slots(state)
        raw_account_no = slots.get("account_no") or slots.get("card_no")
        start_date = slots.get("start_date") or slots.get("date")
        end_date = slots.get("end_date")
        customer_no = resolve_customer_no(state, slots)

        if not raw_account_no:
            return ActionResult(
                result={"reply": "请提供需要查询交易明细的银行卡号或账户号。"}
            )

        normalized_no = normalize_identifier(raw_account_no)
        try:
            data = await finance_client.get_transactions(
                account_no=normalized_no,
                start_date=str(start_date) if start_date else None,
                end_date=str(end_date) if end_date else None,
                customer_no=customer_no,
            )
            items = data.get("list") or data.get("items") or []
            total_count = int(data.get("total_count", len(items)))
            masked_no = mask_identifier(normalized_no)
            rows = _build_tx_rows(items)

            return ActionResult(
                result={
                    "account_no": normalized_no,
                    "total_count": total_count,
                    "transactions": items[:5],
                    "reply": _format_transactions_reply(masked_no, items, total_count),
                },
                receipt={
                    "kind": "transactions",
                    "title": "交易流水单",
                    "sealText": "已核验",
                    "accountNo": masked_no,
                    "totalCount": total_count,
                    "rows": rows,
                }
                if rows
                else None,
            )
        except Exception as e:
            logger.error("查询交易流水失败: %s", e)
            return ActionResult(
                result={"reply": f"查询交易明细失败：{format_action_error(e)}，请核对账号是否正确或稍后重试。"}
            )
