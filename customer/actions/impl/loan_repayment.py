"""贷款正常还款 Action."""
import logging

from customer.actions.base import (
    Action,
    ActionResult,
    format_action_error,
    get_active_slots,
    normalize_identifier,
    resolve_customer_no,
)
from customer.actions.impl.loan_application import parse_loan_amount
from customer.clients.finance_client import finance_client
from customer.domain.state import DialogueState
from customer.security.masking import mask_identifier

logger = logging.getLogger(__name__)


class LoanRepaymentAction(Action):
    """发起贷款账单还款."""

    name = "action_submit_repayment"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = get_active_slots(state)
        customer_no = resolve_customer_no(state, slots) or finance_client.default_customer_no
        raw_bill_no = slots.get("bill_no") or slots.get("related_no")
        raw_account_no = slots.get("account_no") or slots.get("card_no")
        raw_amount = slots.get("repayment_amount") or slots.get("amount")

        if not raw_bill_no or not raw_account_no or raw_amount is None:
            return ActionResult(
                result={"reply": "请提供需要还款的账单编号、扣款银行卡/账户号及还款金额。"}
            )

        try:
            amount_value = parse_loan_amount(raw_amount)
        except (TypeError, ValueError):
            return ActionResult(
                result={"reply": "还款金额格式有误，请输入有效的正数金额（例如 5875.68）。"}
            )

        bill_no = normalize_identifier(raw_bill_no)
        account_no = normalize_identifier(raw_account_no)
        masked_account = mask_identifier(account_no)

        try:
            data = await finance_client.submit_repayment(
                bill_no=bill_no,
                account_no=account_no,
                repayment_amount=amount_value,
                customer_no=customer_no,
            )
            repayment_no = str(data.get("repayment_no") or "")
            status = str(data.get("repayment_status") or data.get("status") or "success")

            return ActionResult(
                result={
                    "repayment_no": repayment_no,
                    "bill_no": bill_no,
                    "account_no": account_no,
                    "repayment_amount": f"{amount_value:.2f}",
                    "status": status,
                    "reply": (
                        f"还款成功！还款流水号【{repayment_no}】，已从账户 {masked_account} 扣款 {amount_value:.2f} 元"
                        f"用于偿还账单【{bill_no}】，当前状态：{status}。"
                    ),
                },
                receipt={
                    "kind": "loan_repayment",
                    "title": "贷款还款回执",
                    "sealText": "已入账",
                    "repaymentNo": repayment_no,
                    "billNo": bill_no,
                    "accountNo": masked_account,
                    "amount": f"{amount_value:.2f}",
                    "status": status,
                },
            )
        except Exception as e:
            logger.error("贷款还款提交失败: %s", e)
            return ActionResult(
                result={"reply": f"贷款还款失败：{format_action_error(e)}，请核对账单编号、账户余额或稍后重试。"}
            )
