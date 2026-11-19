"""查询贷款还款计划、还款账单及逾期记录 Action."""
import asyncio
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

_BILL_STATUS_LABELS = {
    "billed": "待还款",
    "partial_paid": "部分已还",
    "paid": "已结清",
    "overdue": "已逾期",
}


class RepaymentPlanQueryAction(Action):
    """查询贷款合同还款计划、近期还款账单及逾期记录."""

    name = "action_query_repayment_plan"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = get_active_slots(state)
        customer_no = resolve_customer_no(state, slots) or finance_client.default_customer_no
        raw_contract_no = slots.get("contract_no") or slots.get("related_no")
        contract_no = normalize_identifier(raw_contract_no) if raw_contract_no else None

        try:
            schedules_task = (
                finance_client.get_repayment_schedules(contract_no=contract_no, customer_no=customer_no)
                if contract_no
                else asyncio.sleep(0, result=[])
            )
            bills_task = finance_client.get_repayment_bills(
                customer_no=customer_no,
                contract_no=contract_no,
                page_no=1,
                page_size=10,
            )
            overdues_task = finance_client.get_overdues(
                customer_no=customer_no,
                contract_no=contract_no,
                page_no=1,
                page_size=10,
            )
            schedules, bills_data, overdues_data = await asyncio.gather(
                schedules_task,
                bills_task,
                overdues_task,
            )

            bills = bills_data.get("list", []) if isinstance(bills_data, dict) else []
            overdues = overdues_data.get("list", []) if isinstance(overdues_data, dict) else []

            if not schedules and not bills and not overdues:
                target_desc = f"贷款合同 {contract_no}" if contract_no else f"客户 {customer_no}"
                return ActionResult(
                    result={
                        "bills": [],
                        "overdues": [],
                        "reply": f"{target_desc} 当前名下暂无待还账单、还款计划或逾期记录。",
                    }
                )

            lines: list[str] = []
            scope_title = f"合同 {contract_no}" if contract_no else f"客户 {customer_no}"
            lines.append(f"已为您查询 {scope_title} 的贷后还款与逾期信息：")

            formatted_bills: list[dict[str, str]] = []
            if bills:
                lines.append(f"【还款账单（展示最近 {min(len(bills), 5)} 期）】")
                for bill in bills[:5]:
                    bill_no = str(bill.get("bill_no") or "-")
                    outstanding = str(bill.get("outstanding_amount") or "0.00")
                    paid = str(bill.get("paid_amount") or "0.00")
                    raw_status = str(bill.get("bill_status") or "billed")
                    status_label = _BILL_STATUS_LABELS.get(raw_status, raw_status)
                    lines.append(f"- 账单 {bill_no}：待还 {outstanding} 元，已还 {paid} 元，状态：{status_label}")
                    formatted_bills.append(
                        {
                            "billNo": bill_no,
                            "outstandingAmount": outstanding,
                            "paidAmount": paid,
                            "status": status_label,
                        }
                    )

            if schedules:
                lines.append(f"【还款计划（共 {len(schedules)} 期，展示前 {min(len(schedules), 3)} 期）】")
                for item in schedules[:3]:
                    lines.append(
                        f"- 第 {item.get('period_no')} 期（到期日 {item.get('due_date')}）："
                        f"本金 {item.get('principal_amount')} 元 + 利息 {item.get('interest_amount')} 元"
                    )

            if overdues:
                lines.append(f"【逾期提示】当前存在 {len(overdues)} 条逾期记录：")
                for ovd in overdues[:3]:
                    lines.append(
                        f"- 逾期单 {ovd.get('overdue_no')}：已逾期 {ovd.get('overdue_days')} 天，"
                        f"逾期总额 {ovd.get('overdue_total_amount')} 元"
                    )
            else:
                lines.append("【逾期提示】当前无逾期记录，信用状态良好。")

            return ActionResult(
                result={
                    "contract_no": contract_no,
                    "bills": formatted_bills,
                    "overdue_count": len(overdues),
                    "reply": "\n".join(lines),
                },
                receipt={
                    "kind": "repayment_plan",
                    "title": "还款账单凭证",
                    "sealText": "已核验",
                    "scopeLabel": scope_title,
                    "billCount": len(bills),
                    "overdueCount": len(overdues),
                    "bills": formatted_bills,
                },
            )
        except Exception as e:
            logger.error("查询还款计划与账单失败: %s", e)
            return ActionResult(
                result={"reply": f"查询还款信息失败：{format_action_error(e)}，请核对合同号是否正确或稍后重试。"}
            )
