"""五大金融任务型流程、对象消息填槽及全链路多轮对话集成测试."""
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from customer.domain.messages import BotMessage, MessageObject, MessageType, UserMessage
from customer.domain.state import DialogueState
from customer.engine.builder import build_engine
from customer.plan.command import ResumeTaskCommand, SetSlotsCommand, StartFlowCommand
from customer.plan.turn_plan import ClarifyReason, KnowledgeTurnPlan, TaskTurnPlan, TurnPlan


def _text_msg(text: str, msg_id: str, sender_id: str = "CUST00000001") -> UserMessage:
    return UserMessage(
        sender_id=sender_id,
        message_id=msg_id,
        type=MessageType.TEXT,
        text=text,
    )


def _object_msg(obj_type: str, obj_id: str, msg_id: str, title: str = "", sender_id: str = "CUST00000001") -> UserMessage:
    return UserMessage(
        sender_id=sender_id,
        message_id=msg_id,
        type=MessageType.OBJECT,
        object=MessageObject(type=obj_type, id=obj_id, title=title or obj_id),
    )


class TestFinanceEndToEndFlows(unittest.IsolatedAsyncioTestCase):
    """覆盖 5 大金融任务流程、任务切换恢复、对象卡片填槽与知识问答的全链路测试."""

    async def test_balance_query_with_account_object_message(self):
        engine = build_engine()
        state = DialogueState(sender_id="CUST00000001")
        mock_planner = AsyncMock()
        engine.turn_planner = mock_planner

        mock_planner.plan.return_value = TurnPlan(
            task=TaskTurnPlan(commands=[StartFlowCommand(command="start_flow", flow="account_balance_query")])
        )
        r1 = await engine.process_message(state, _text_msg("帮我查账户余额", "m1"))
        self.assertTrue(any("银行卡号或账户号" in m.text for m in r1.messages))

        with patch(
            "customer.actions.impl.account_balance.finance_client.get_account",
            new=AsyncMock(return_value={"account_status": "active", "balance_amount": "8800.00", "frozen_amount": "300.00"}),
        ) as mock_get:
            r2 = await engine.process_message(
                state,
                _object_msg("account", "ACC0000000001", "m2", title="储蓄账户"),
            )

        mock_get.assert_awaited_once_with(account_no="ACC0000000001", customer_no="CUST00000001")
        self.assertTrue(any("8500.00" in m.text for m in r2.messages))
        self.assertIsNone(state.tasks.active)

    async def test_transaction_history_query_single_turn(self):
        engine = build_engine()
        state = DialogueState(sender_id="CUST00000001")
        mock_planner = AsyncMock()
        engine.turn_planner = mock_planner
        mock_planner.plan.return_value = TurnPlan(
            task=TaskTurnPlan(
                commands=[
                    StartFlowCommand(command="start_flow", flow="transaction_history_query"),
                    SetSlotsCommand(command="set_slots", slots={"account_no": "ACC0000000001", "start_date": "2026-11-01"}),
                ]
            )
        )

        with patch(
            "customer.actions.impl.transaction_query.finance_client.get_transactions",
            new=AsyncMock(
                return_value={
                    "total_count": 1,
                    "list": [
                        {
                            "transaction_at": "2026-11-18 12:00:00",
                            "transaction_type": "payment",
                            "transaction_amount": "128.00",
                            "currency_code": "CNY",
                            "merchant_name": "咖啡门店",
                            "transaction_status": "success",
                        }
                    ],
                }
            ),
        ):
            res = await engine.process_message(state, _text_msg("查一下 ACC0000000001 本月交易明细", "m1"))

        self.assertTrue(any("咖啡门店" in m.text and "128.00" in m.text for m in res.messages))
        self.assertIsNone(state.tasks.active)

    async def test_loan_application_with_task_switch_and_resume(self):
        engine = build_engine()
        state = DialogueState(sender_id="CUST00000001")
        mock_planner = AsyncMock()
        engine.turn_planner = mock_planner

        # 1. 开始贷款申请
        mock_planner.plan.return_value = TurnPlan(
            task=TaskTurnPlan(commands=[StartFlowCommand(command="start_flow", flow="loan_application")])
        )
        r1 = await engine.process_message(state, _text_msg("我要申请消费贷款", "m1"))
        self.assertTrue(any("贷款金额" in m.text for m in r1.messages))
        loan_task_id = state.tasks.active.task_id

        # 2. 填写贷款金额，系统追问期限
        mock_planner.plan.return_value = TurnPlan(
            task=TaskTurnPlan(commands=[SetSlotsCommand(command="set_slots", slots={"loan_amount": "50000"})])
        )
        r2 = await engine.process_message(state, _text_msg("50000", "m2"))
        self.assertTrue(any("贷款期限" in m.text for m in r2.messages))

        # 3. 中途插入余额查询（暂停贷款流程）
        mock_planner.plan.return_value = TurnPlan(
            task=TaskTurnPlan(
                commands=[
                    StartFlowCommand(command="start_flow", flow="account_balance_query"),
                    SetSlotsCommand(command="set_slots", slots={"account_no": "ACC0000000001"}),
                ]
            )
        )
        with patch(
            "customer.actions.impl.account_balance.finance_client.get_account",
            new=AsyncMock(return_value={"account_status": "active", "balance_amount": "10000.00", "frozen_amount": "0.00"}),
        ):
            r3 = await engine.process_message(state, _text_msg("先帮我查下 ACC0000000001 余额", "m3"))
        self.assertTrue(any("暂停" in m.text for m in r3.messages))
        self.assertTrue(any("10000.00" in m.text for m in r3.messages))
        self.assertEqual(len(state.tasks.paused), 1)

        # 4. 恢复之前的贷款申请流程
        mock_planner.plan.return_value = TurnPlan(
            task=TaskTurnPlan(commands=[ResumeTaskCommand(command="resume_task", task_id=loan_task_id)])
        )
        r4 = await engine.process_message(state, _text_msg("继续办理刚才的贷款", "m4"))
        self.assertTrue(any("继续贷款申请" in m.text for m in r4.messages))
        self.assertTrue(any("贷款期限" in m.text for m in r4.messages))
        self.assertEqual(state.tasks.active.slots.get("loan_amount"), "50000")

        # 5. 补充期限完成进件
        mock_planner.plan.return_value = TurnPlan(
            task=TaskTurnPlan(commands=[SetSlotsCommand(command="set_slots", slots={"loan_term": "12"})])
        )
        with patch(
            "customer.actions.impl.loan_application.finance_client.apply_loan",
            new=AsyncMock(return_value={"application_no": "LAP202611180088", "application_status": "submitted"}),
        ):
            r5 = await engine.process_message(state, _text_msg("12期", "m5"))
        self.assertTrue(any("LAP202611180088" in m.text for m in r5.messages))
        self.assertIsNone(state.tasks.active)

    async def test_card_loss_report_with_card_object_message(self):
        engine = build_engine()
        state = DialogueState(sender_id="CUST00000001")
        mock_planner = AsyncMock()
        engine.turn_planner = mock_planner

        mock_planner.plan.return_value = TurnPlan(
            task=TaskTurnPlan(commands=[StartFlowCommand(command="start_flow", flow="card_loss_report")])
        )
        r1 = await engine.process_message(state, _text_msg("我的信用卡丢了要挂失", "m1"))
        self.assertTrue(any("银行卡号或信用卡号" in m.text for m in r1.messages))

        r2 = await engine.process_message(state, _object_msg("card", "ACC0000000002", "m2", title="白金信用卡"))
        self.assertTrue(any("挂失的主要原因" in m.text for m in r2.messages))

        mock_planner.plan.return_value = TurnPlan(
            task=TaskTurnPlan(commands=[SetSlotsCommand(command="set_slots", slots={"loss_reason": "卡片丢失"})])
        )
        with patch(
            "customer.actions.impl.card_loss.finance_client.change_account_status",
            new=AsyncMock(return_value={"status_history_id": 202, "current_status": "loss_reported"}),
        ) as mock_loss:
            r3 = await engine.process_message(state, _text_msg("卡片丢了", "m3"))

        mock_loss.assert_awaited_once_with(
            account_no="ACC0000000002",
            target_status="loss_reported",
            reason="卡片丢失",
            customer_no="CUST00000001",
        )
        self.assertTrue(any("紧急挂失" in m.text for m in r3.messages))
        self.assertIsNone(state.tasks.active)

    async def test_complaint_ticket_flow(self):
        engine = build_engine()
        state = DialogueState(sender_id="CUST00000001")
        mock_planner = AsyncMock()
        engine.turn_planner = mock_planner

        mock_planner.plan.return_value = TurnPlan(
            task=TaskTurnPlan(
                commands=[
                    StartFlowCommand(command="start_flow", flow="complaint_ticket"),
                    SetSlotsCommand(command="set_slots", slots={"ticket_category": "扣费异常"}),
                ]
            )
        )
        r1 = await engine.process_message(state, _text_msg("我要投诉扣费异常", "m1"))
        self.assertTrue(any("详细描述" in m.text for m in r1.messages))

        mock_planner.plan.return_value = TurnPlan(
            task=TaskTurnPlan(commands=[SetSlotsCommand(command="set_slots", slots={"ticket_description": "凌晨被莫名扣费200元"})])
        )
        with patch(
            "customer.actions.impl.ticket_action.finance_client.create_support_ticket",
            new=AsyncMock(return_value={"ticket_no": "TKT202611180077", "ticket_status": "submitted"}),
        ):
            r2 = await engine.process_message(state, _text_msg("凌晨被莫名扣费200元", "m2"))

        self.assertTrue(any("TKT202611180077" in m.text for m in r2.messages))
        self.assertIsNone(state.tasks.active)

    async def test_object_message_without_active_task_triggers_clarify(self):
        engine = build_engine()
        state = DialogueState(sender_id="CUST00000001")
        engine.clarify_response.clarify_response = AsyncMock(
            return_value=[BotMessage(text="已收到您的银行卡卡片，请问需要查余额还是办理挂失？")]
        )

        res = await engine.process_message(state, _object_msg("card", "ACC0000000009", "m1", title="借记卡"))
        engine.clarify_response.clarify_response.assert_awaited_once()
        call_kwargs = engine.clarify_response.clarify_response.await_args.kwargs
        self.assertEqual(call_kwargs["reason"], ClarifyReason.OBJECT_REQUIRES_INTENT)
        self.assertEqual(state.shared.focused_object.id, "ACC0000000009")
        self.assertTrue(any("银行卡卡片" in m.text for m in res.messages))

    async def test_knowledge_consultation_e2e(self):
        engine = build_engine()
        state = DialogueState(sender_id="CUST00000001")
        mock_planner = AsyncMock()
        mock_planner.plan.return_value = TurnPlan(
            knowledge=KnowledgeTurnPlan(intents=["wealth_product_info"])
        )
        engine.turn_planner = mock_planner
        engine.knowledge_handler.knowledge_responder.respond = AsyncMock(
            return_value=BotMessage(text="我行提供 R2 稳健型理财产品 WLT_STEADY_01，请注意非保本浮动收益风险。")
        )

        with patch(
            "customer.handlers.knowledge.provider.finance_client.get_wealth_products",
            new=AsyncMock(return_value=[{"product_code": "WLT_STEADY_01", "risk_level": "R2"}]),
        ):
            res = await engine.process_message(state, _text_msg("有什么稳健型的理财产品？", "m1"))

        self.assertTrue(any("WLT_STEADY_01" in m.text for m in res.messages))


if __name__ == "__main__":
    unittest.main()
