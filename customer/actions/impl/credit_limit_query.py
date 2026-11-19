"""查询客户授信额度 Action."""
import logging

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


class CreditLimitQueryAction(Action):
    """查询客户名下可用授信额度."""

    name = "action_query_credit_limit"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = get_active_slots(state)
        customer_no = resolve_customer_no(state, slots) or finance_client.default_customer_no
        product_code = slots.get("product_code")

        try:
            limits = await finance_client.get_credit_limits(
                customer_no=customer_no,
                product_code=str(product_code) if product_code else None,
            )
            if not limits:
                return ActionResult(
                    result={
                        "credit_limits": [],
                        "reply": f"客户 {customer_no} 当前名下暂无有效授信额度记录，如需申请消费或经营贷款可联系客服或前往手机银行办理授信。",
                    }
                )

            lines = [f"为您查询到客户 {customer_no} 名下共 {len(limits)} 笔授信额度："]
            formatted_items: list[dict[str, str]] = []
            for idx, item in enumerate(limits[:5], start=1):
                limit_no = str(item.get("limit_no") or "-")
                p_code = str(item.get("product_code") or "LOAN")
                total_amt = str(item.get("total_limit_amount") or "0.00")
                avail_amt = str(item.get("available_limit_amount") or "0.00")
                frozen_amt = str(item.get("frozen_limit_amount") or "0.00")
                valid_to = str(item.get("valid_to") or "-")
                lines.append(
                    f"{idx}. 产品 {p_code}（额度编号 {limit_no}）：可用 {avail_amt} 元 / 总额 {total_amt} 元"
                    f"（冻结 {frozen_amt} 元，有效期至 {valid_to}）"
                )
                formatted_items.append(
                    {
                        "limitNo": limit_no,
                        "productCode": p_code,
                        "totalAmount": total_amt,
                        "availableAmount": avail_amt,
                        "frozenAmount": frozen_amt,
                        "validTo": valid_to,
                    }
                )

            primary = formatted_items[0]
            return ActionResult(
                result={
                    "credit_limits": formatted_items,
                    "available_limit_amount": primary["availableAmount"],
                    "reply": "\n".join(lines),
                },
                receipt={
                    "kind": "credit_limit",
                    "title": "授信额度凭证",
                    "sealText": "已核验",
                    "customerNo": customer_no,
                    "items": formatted_items,
                },
            )
        except Exception as e:
            logger.error("查询授信额度失败: %s", e)
            return ActionResult(
                result={"reply": f"查询授信额度失败：{format_action_error(e)}，请稍后重试或联系人工客服。"}
            )
