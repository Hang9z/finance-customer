"""查询贷款申请审批进度 Action."""
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

_LOAN_STATUS_LABELS = {
    "submitted": "审核中",
    "processing": "审批处理中",
    "approved": "审批通过",
    "rejected": "审批未通过",
    "cancelled": "已取消",
    "expired": "已过期",
}


class LoanProgressQueryAction(Action):
    """查询贷款申请进度与审批记录."""

    name = "action_query_loan_progress"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = get_active_slots(state)
        raw_application_no = slots.get("application_no") or slots.get("related_no")
        customer_no = resolve_customer_no(state, slots)

        if not raw_application_no:
            return ActionResult(
                result={"reply": "请提供您需要查询进度的贷款申请编号（例如 LAP 开头的编号）。"}
            )

        normalized_no = normalize_identifier(raw_application_no)
        try:
            data = await finance_client.get_loan_application(
                application_no=normalized_no,
                customer_no=customer_no,
            )
            info = data.get("application_info") or {}
            approvals = data.get("approval_records") or []
            contract = data.get("contract_info")

            app_no = str(info.get("application_no") or normalized_no)
            apply_amount = info.get("apply_amount", "0.00")
            apply_term = info.get("apply_term_months", "-")
            raw_status = str(info.get("application_status") or "submitted")
            status_text = _LOAN_STATUS_LABELS.get(raw_status, raw_status)
            submitted_at = str(info.get("submitted_at") or "-")

            reply = (
                f"贷款申请编号【{app_no}】申请金额 {apply_amount} 元，期限 {apply_term} 个月，"
                f"当前审批状态为【{status_text}】，提交时间：{submitted_at}。"
            )
            extra_notes: list[str] = []
            if approvals:
                latest_comment = approvals[-1].get("approval_comment")
                if latest_comment:
                    extra_notes.append(f"审批意见：{latest_comment}")
            if isinstance(contract, dict) and contract.get("contract_no"):
                extra_notes.append(f"已生成贷款合同：{contract['contract_no']}")
            if extra_notes:
                reply = f"{reply}（{'；'.join(extra_notes)}）"

            return ActionResult(
                result={
                    "application_no": app_no,
                    "loan_amount": str(apply_amount),
                    "loan_term": str(apply_term),
                    "status": raw_status,
                    "reply": reply,
                },
                receipt={
                    "kind": "loan_progress",
                    "title": "贷款进度回执",
                    "sealText": "已核验",
                    "applicationNo": app_no,
                    "amount": str(apply_amount),
                    "termMonths": str(apply_term),
                    "status": status_text,
                    "submittedAt": submitted_at,
                },
            )
        except Exception as e:
            logger.error("查询贷款进度失败: %s", e)
            return ActionResult(
                result={"reply": f"查询贷款进度失败：{format_action_error(e)}，请核对申请编号是否正确或联系人工客服。"}
            )
