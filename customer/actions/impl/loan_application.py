"""提交消费贷款申请 Action."""
import logging
import re

from customer.actions.base import (
    Action,
    ActionResult,
    format_action_error,
    get_active_slots,
    resolve_customer_no,
)
from customer.clients.finance_client import finance_client
from customer.domain.state import DialogueState

logger = logging.getLogger(__name__)

_AMOUNT_RE = re.compile(r"^([+-]?\d+(?:\.\d+)?)\s*(亿|万|千|百)?$")
_TERM_RE = re.compile(r"^(\d+)\s*(年|个月|月|期)?$")
_AMOUNT_UNIT_MULTIPLIER = {
    "亿": 100_000_000.0,
    "万": 10_000.0,
    "千": 1_000.0,
    "百": 100.0,
}


def parse_loan_amount(raw: object) -> float:
    """将口语化贷款金额（如 '10万元'、'50,000元'、'1.5万'）解析为数值（元）."""
    if isinstance(raw, (int, float)):
        value = float(raw)
        if value <= 0:
            raise ValueError("贷款金额必须大于 0")
        return value

    text = str(raw).strip().replace(",", "").replace("，", "")
    text = re.sub(r"(?:人民币|CNY|RMB|元|块)+$", "", text, flags=re.IGNORECASE).strip()
    match = _AMOUNT_RE.match(text)
    if not match:
        raise ValueError(f"无法解析贷款金额: {raw}")

    num = float(match.group(1))
    unit = match.group(2)
    value = num * _AMOUNT_UNIT_MULTIPLIER.get(unit, 1.0)
    if value <= 0:
        raise ValueError("贷款金额必须大于 0")
    return value


def parse_loan_term(raw: object) -> int:
    """将口语化贷款期限（如 '36期'、'12个月'、'2年'）解析为月数整数."""
    if isinstance(raw, int) and not isinstance(raw, bool):
        if raw <= 0:
            raise ValueError("贷款期限必须大于 0")
        return raw

    text = str(raw).strip()
    match = _TERM_RE.match(text)
    if not match:
        raise ValueError(f"无法解析贷款期限: {raw}")

    num = int(match.group(1))
    unit = match.group(2)
    months = num * 12 if unit == "年" else num
    if months <= 0:
        raise ValueError("贷款期限必须大于 0")
    return months


class LoanApplicationAction(Action):
    """提交消费贷款申请."""

    name = "action_apply_loan"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = get_active_slots(state)
        customer_no = resolve_customer_no(state, slots) or finance_client.default_customer_no
        product_code = slots.get("product_code") or slots.get("loan_type") or "LOAN_CONSUMER_STD"
        raw_amount = slots.get("loan_amount") or slots.get("amount")
        raw_term = slots.get("loan_term") or slots.get("term")
        loan_purpose = slots.get("loan_purpose") or slots.get("purpose") or "consume"
        limit_no = slots.get("limit_no")

        if raw_amount is None or raw_term is None:
            return ActionResult(
                result={"reply": "请先提供完整的贷款申请金额和期望还款期限（月）。"}
            )

        try:
            apply_amount = parse_loan_amount(raw_amount)
            loan_term = parse_loan_term(raw_term)
        except (TypeError, ValueError):
            return ActionResult(
                result={"reply": "贷款金额或期限格式有误，请提供有效的数字（例如金额 10000，期限 12 个月）。"}
            )

        try:
            data = await finance_client.apply_loan(
                customer_no=customer_no,
                product_code=str(product_code),
                apply_amount=apply_amount,
                loan_term=loan_term,
                loan_purpose=str(loan_purpose),
                limit_no=str(limit_no) if limit_no else None,
            )
            application_no = data.get("application_no", "")
            status = data.get("application_status") or data.get("status", "submitted")

            return ActionResult(
                result={
                    "application_no": application_no,
                    "product_code": product_code,
                    "loan_amount": f"{apply_amount:.2f}",
                    "loan_term": loan_term,
                    "status": status,
                    "reply": (
                        f"您的贷款申请已成功提交！申请编号为【{application_no}】，"
                        f"申请金额 {apply_amount:.2f} 元，期限 {loan_term} 个月，"
                        f"当前状态为【{status}】，预计 1 个工作日内完成审批。"
                    ),
                }
            )
        except Exception as e:
            logger.error("提交贷款申请失败: %s", e)
            return ActionResult(
                result={"reply": f"贷款申请提交失败：{format_action_error(e)}，请核对授信额度与产品参数或联系人工客服。"}
            )
