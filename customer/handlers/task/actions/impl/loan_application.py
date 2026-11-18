"""提交贷款申请 Action."""
import logging
from customer.clients.finance_client import finance_client
from customer.domain.state import DialogueState
from customer.handlers.task.actions.base import Action, ActionResult

logger = logging.getLogger(__name__)


class LoanApplicationAction(Action):
    """提交消费贷款申请."""

    name = "action_apply_loan"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.tasks.active.slots if state.tasks.active else {}
        customer_no = slots.get("customer_no") or "CUST00000001"
        product_code = slots.get("loan_type") or slots.get("product_code") or "LOAN_CONSUME_01"
        apply_amount = slots.get("loan_amount") or slots.get("amount") or "10000"
        loan_term = slots.get("loan_term") or slots.get("term") or 12
        loan_purpose = slots.get("loan_purpose") or slots.get("purpose") or "个人日常消费"

        try:
            data = await finance_client.apply_loan(
                customer_no=customer_no,
                product_code=str(product_code),
                apply_amount=apply_amount,
                loan_term=int(loan_term),
                loan_purpose=loan_purpose,
            )
            application_no = data.get("application_no", "APP_TEMP_001")
            status = data.get("status", "submitted")

            return ActionResult(
                success=True,
                result={
                    "application_no": application_no,
                    "status": status,
                    "amount": apply_amount,
                    "term": loan_term,
                    "reply": f"您的贷款申请已成功提交！申请编号为【{application_no}】，申请金额 {apply_amount} 元，期限 {loan_term} 个月，当前状态为审核中，预计 1 个工作日内完成审批。"
                }
            )
        except Exception as e:
            logger.error("提交贷款申请失败: %s", e)
            return ActionResult(
                success=False,
                error=str(e),
                result={"reply": f"贷款申请提交失败，请稍后重试或联系人工客服。({e})"}
            )
