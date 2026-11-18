"""金融任务型业务 Action 与 FinanceClient 单元测试."""
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from customer.actions.builder import registry_action
from customer.actions.impl.account_balance import AccountBalanceQueryAction
from customer.actions.impl.card_loss import CardLossAction
from customer.actions.impl.loan_application import LoanApplicationAction
from customer.actions.impl.ticket_action import ComplaintTicketAction
from customer.actions.impl.transaction_query import TransactionQueryAction
from customer.actions.registry import ActionRegistry
from customer.clients.finance_client import FinanceClient
from customer.domain.state import DialogueState, TaskInstance
from customer.handlers.task.flow.loader import FlowLoader
from customer.handlers.task.flow.steps import ActionFlowStep


def _build_state(flow_id: str, slots: dict, sender_id: str = "CUST00000001") -> DialogueState:
    state = DialogueState(sender_id=sender_id)
    state.tasks.active = TaskInstance(flow_id=flow_id, slots=slots)
    return state


class TestFinanceActionRegistration(unittest.TestCase):
    """验证金融 Action 自动扫描注册与 YAML 引用一致性."""

    def test_all_yaml_actions_registered(self):
        registry = ActionRegistry()
        registry_action(registry)

        expected = {
            "action_query_account_balance",
            "action_query_transactions",
            "action_apply_loan",
            "action_report_card_loss",
            "action_create_complaint_ticket",
        }
        self.assertTrue(expected.issubset(set(registry.actions.keys())))

        catalog = FlowLoader().load(Path("customer/flow_config/user_flows.yml"))
        for flow_id, flow in catalog.flows.items():
            for step in flow.steps:
                if isinstance(step, ActionFlowStep):
                    self.assertIn(
                        step.action,
                        registry.actions,
                        f"Flow '{flow_id}' references unregistered action '{step.action}'",
                    )


class TestFinanceActionsExecution(unittest.IsolatedAsyncioTestCase):
    """验证 5 个金融 Action 的业务逻辑与字段映射."""

    async def test_account_balance_query_action(self):
        action = AccountBalanceQueryAction()
        state = _build_state("account_balance_query", {"account_no": "ACC0000000001"})

        with patch(
            "customer.actions.impl.account_balance.finance_client.get_account",
            new=AsyncMock(
                return_value={
                    "account_status": "active",
                    "balance_amount": "12500.50",
                    "frozen_amount": "500.00",
                }
            ),
        ) as mock_get:
            res = await action.run(state)

        mock_get.assert_awaited_once_with(account_no="ACC0000000001", customer_no="CUST00000001")
        self.assertEqual(res.result["balance"], "12500.50")
        self.assertEqual(res.result["available_balance"], "12000.50")
        self.assertIn("12000.50", res.result["reply"])
        self.assertIn("正常", res.result["reply"])

    async def test_transaction_query_action(self):
        action = TransactionQueryAction()
        state = _build_state(
            "transaction_history_query",
            {"account_no": "ACC0000000001", "start_date": "2026-11-01", "end_date": "2026-11-18"},
        )

        with patch(
            "customer.actions.impl.transaction_query.finance_client.get_transactions",
            new=AsyncMock(
                return_value={
                    "total_count": 2,
                    "list": [
                        {
                            "transaction_at": "2026-11-17 10:00:00",
                            "transaction_type": "payment",
                            "transaction_amount": "199.00",
                            "currency_code": "CNY",
                            "merchant_name": "测试商户",
                            "transaction_status": "success",
                        },
                        {
                            "transaction_at": "2026-11-16 09:00:00",
                            "transaction_type": "deposit",
                            "transaction_amount": "2000.00",
                            "currency_code": "CNY",
                            "counterparty_name": "工资代发",
                            "transaction_status": "success",
                        },
                    ],
                }
            ),
        ) as mock_tx:
            res = await action.run(state)

        mock_tx.assert_awaited_once_with(
            account_no="ACC0000000001",
            start_date="2026-11-01",
            end_date="2026-11-18",
            customer_no="CUST00000001",
        )
        self.assertEqual(res.result["total_count"], 2)
        self.assertEqual(len(res.result["transactions"]), 2)
        self.assertIn("测试商户", res.result["reply"])
        self.assertIn("工资代发", res.result["reply"])

    async def test_card_loss_action(self):
        action = CardLossAction()
        state = _build_state(
            "card_loss_report",
            {"card_no": "ACC0000000002", "loss_reason": "卡片遗失"},
        )

        with patch(
            "customer.actions.impl.card_loss.finance_client.change_account_status",
            new=AsyncMock(return_value={"status_history_id": 101, "current_status": "loss_reported"}),
        ) as mock_loss:
            res = await action.run(state)

        mock_loss.assert_awaited_once_with(
            account_no="ACC0000000002",
            target_status="loss_reported",
            reason="卡片遗失",
            customer_no="CUST00000001",
        )
        self.assertEqual(res.result["status"], "loss_reported")
        self.assertEqual(res.result["status_history_id"], 101)
        self.assertIn("紧急挂失", res.result["reply"])

    async def test_loan_application_action(self):
        action = LoanApplicationAction()
        state = _build_state(
            "loan_application",
            {
                "loan_amount": "50000",
                "loan_term": "12",
                "product_code": "LOAN_CONSUMER_STD",
                "loan_purpose": "家庭装修",
            },
        )

        with patch(
            "customer.actions.impl.loan_application.finance_client.apply_loan",
            new=AsyncMock(return_value={"application_no": "LAP202611180001", "application_status": "submitted"}),
        ) as mock_loan:
            res = await action.run(state)

        mock_loan.assert_awaited_once_with(
            customer_no="CUST00000001",
            product_code="LOAN_CONSUMER_STD",
            apply_amount=50000.0,
            loan_term=12,
            loan_purpose="家庭装修",
            limit_no=None,
        )
        self.assertEqual(res.result["application_no"], "LAP202611180001")
        self.assertEqual(res.result["status"], "submitted")
        self.assertIn("LAP202611180001", res.result["reply"])

    async def test_loan_application_invalid_number(self):
        action = LoanApplicationAction()
        state = _build_state("loan_application", {"loan_amount": "abc", "loan_term": "12"})
        res = await action.run(state)
        self.assertIn("格式有误", res.result["reply"])

    async def test_complaint_ticket_action(self):
        action = ComplaintTicketAction()
        state = _build_state(
            "complaint_ticket",
            {
                "ticket_category": "扣费异常",
                "ticket_description": "昨晚重复扣款 200 元",
                "related_no": "TXN202611170099",
            },
        )

        with patch(
            "customer.actions.impl.ticket_action.finance_client.create_support_ticket",
            new=AsyncMock(return_value={"ticket_no": "TKT202611180001", "ticket_status": "submitted"}),
        ) as mock_ticket:
            res = await action.run(state)

        mock_ticket.assert_awaited_once_with(
            customer_no="CUST00000001",
            category="扣费异常",
            description="昨晚重复扣款 200 元",
            related_no="TXN202611170099",
        )
        self.assertEqual(res.result["ticket_no"], "TKT202611180001")
        self.assertIn("TKT202611180001", res.result["reply"])


class TestFinanceClientContract(unittest.IsolatedAsyncioTestCase):
    """验证 FinanceClient 请求头与 finance-data 接口契约一致."""

    async def test_headers_include_channel_code(self):
        client = FinanceClient(base_url="http://127.0.0.1:8000/api/v1")
        headers = client._build_headers("CUST00000001")
        self.assertEqual(headers["Authorization"], "Bearer CUST00000001")
        self.assertEqual(headers["X-Channel-Code"], "MOBILE_BANK")
        self.assertTrue(headers["X-Request-Id"])

    async def test_apply_loan_resolves_limit_and_sends_finance_data_schema(self):
        client = FinanceClient(base_url="http://127.0.0.1:8000/api/v1")

        def make_resp(data: dict):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"code": "OK", "data": data}
            return resp

        get_mock = AsyncMock(
            side_effect=[
                make_resp({"list": [{"limit_no": "LMT0001", "available_limit_amount": "100000.00", "product_code": "LOAN_CONSUMER_STD"}]}),
                make_resp({"product_detail": {"repayment_method": "equal_principal_interest"}}),
            ]
        )
        post_mock = AsyncMock(
            return_value=make_resp({"application_no": "LAP0001", "application_status": "submitted"})
        )

        mock_http = MagicMock()
        mock_http.get = get_mock
        mock_http.post = post_mock

        with patch.object(FinanceClient, "_http", return_value=mock_http):
            data = await client.apply_loan(
                customer_no="CUST00000001",
                product_code="LOAN_CONSUMER_STD",
                apply_amount=20000,
                loan_term=12,
                loan_purpose="日常消费",
            )

        self.assertEqual(data["application_no"], "LAP0001")
        sent_payload = post_mock.await_args.kwargs["json"]
        self.assertEqual(sent_payload["limit_no"], "LMT0001")
        self.assertEqual(sent_payload["apply_term_months"], 12)
        self.assertEqual(sent_payload["repayment_method"], "equal_principal_interest")
        self.assertEqual(sent_payload["apply_amount"], "20000.00")

    async def test_create_support_ticket_sends_finance_data_schema(self):
        client = FinanceClient(base_url="http://127.0.0.1:8000/api/v1")
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"code": "OK", "data": {"ticket_no": "TKT0001", "ticket_status": "submitted"}}
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value=resp)

        with patch.object(FinanceClient, "_http", return_value=mock_http):
            data = await client.create_support_ticket(
                customer_no="CUST00000001",
                category="转账异常",
                description="跨行转账未到账",
                related_no="TXN001",
            )

        self.assertEqual(data["ticket_no"], "TKT0001")
        sent_payload = mock_http.post.await_args.kwargs["json"]
        sent_headers = mock_http.post.await_args.kwargs["headers"]
        self.assertEqual(sent_payload["ticket_type"], "转账异常")
        self.assertEqual(sent_payload["related_type"], "none")
        self.assertIn("TXN001", sent_payload["ticket_content"])
        self.assertEqual(sent_headers["X-Operator-No"], "EMP000006")


if __name__ == "__main__":
    unittest.main()
