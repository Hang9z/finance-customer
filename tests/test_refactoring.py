import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from customer.handlers.task.actions import ActionResult
from customer.handlers.task.actions.builder import registry_action
from customer.handlers.task.actions import ActionRegistry
from customer.domain.messages import MessageType, UserMessage
from customer.domain.state import DialogueState, TaskInstance
from customer.engine.builder import build_engine
from customer.handlers.task.flow.loader import FlowLoader
from customer.handlers.task.flow.models import FlowCatalog
from customer.plan.command import CancelTaskCommand, ResumeTaskCommand, SetSlotsCommand, StartFlowCommand
from customer.plan.turn_plan import ChitchatTurnPlan, ClarifyReason, KnowledgeTurnPlan, TaskTurnPlan, TurnPlan
from customer.plan.turn_plan_validation import TurnPlanValidation


class TestRefactoringIntegrity(unittest.TestCase):
    """验证重构后的架构、依赖注入、校验逻辑与端到端运行能力。"""

    def test_01_no_legacy_imports_in_customer(self):
        """验证整个 customer 源码目录下无旧模块路径导入。"""
        patterns = [
            r'customer\.task\b',
            r'customer\.chitchat\b',
            r'customer\.clarify\b',
            r'turn_plan_validai',
            r'customer\.domain\.dialogue_state\b',
            r'from\s+.*dialogue_state\s+import',
            r'import\s+.*dialogue_state',
        ]
        errors = []
        for root, _, files in os.walk("customer"):
            for f in files:
                if f.endswith(".py"):
                    p = Path(root, f)
                    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                        if line.strip().startswith("#"):
                            continue
                        for pat in patterns:
                            if re.search(pat, line):
                                errors.append(f"{p}:{i} -> {line.strip()}")
        self.assertEqual(errors, [], f"Found legacy import references: {errors}")

    def test_02_directory_structure_constraints(self):
        """验证目录结构严格符合规范：包含中台客户端、impl实现包与对称Handler。"""
        self.assertTrue(Path("customer/engine").is_dir(), "customer/engine must exist")
        self.assertFalse(Path("customer/core").exists(), "customer/core must NOT exist")
        self.assertTrue(Path("customer/clients").is_dir(), "customer/clients must exist")
        self.assertTrue(Path("customer/handlers/task/actions").is_dir(), "customer/handlers/task/actions must exist")
        self.assertTrue(Path("customer/handlers/task/actions/impl").is_dir(), "customer/handlers/task/actions/impl must exist")
        self.assertTrue(Path("customer/handlers/task").is_dir(), "customer/handlers/task must exist")
        self.assertTrue(Path("customer/handlers/chitchat").is_dir(), "customer/handlers/chitchat must exist")
        self.assertTrue(Path("customer/handlers/clarify").is_dir(), "customer/handlers/clarify must exist")
        self.assertTrue(Path("customer/handlers/knowledge").is_dir(), "customer/handlers/knowledge must exist")
        self.assertTrue(Path("customer/handlers/knowledge/__init__.py").is_file(), "customer/handlers/knowledge/__init__.py must exist")

        # 旧路径必须彻底清除
        self.assertFalse(Path("customer/task").exists(), "customer/task must be deleted")
        self.assertFalse(Path("customer/chitchat").exists(), "customer/chitchat must be deleted")
        self.assertFalse(Path("customer/clarify").exists(), "customer/clarify must be deleted")
        self.assertFalse(Path("customer/domain/dialogue_state.py").exists(), "customer/domain/dialogue_state.py must be deleted")
        self.assertFalse(Path("customer/plan/turn_plan_validaiton.py").exists(), "customer/plan/turn_plan_validaiton.py must be deleted")
        self.assertTrue(Path("customer/plan/turn_plan_validation.py").is_file(), "customer/plan/turn_plan_validation.py must exist")

    def test_03_flow_loader(self):
        """验证 FlowLoader 解析 YAML 正常。"""
        flow_file = Path("customer/flow_config/user_flows.yml")
        catalog = FlowLoader().load(flow_file)
        self.assertIsInstance(catalog, FlowCatalog)
        self.assertIn("order_status_query", catalog.flows)
        self.assertIn("logistics_tracking", catalog.flows)
        self.assertIn("refund_request", catalog.flows)

    def test_04_action_registry_discovery(self):
        """验证 ActionRegistry 通过 actions.builder 自动扫描注册动作。"""
        reg = ActionRegistry()
        registry_action(reg)
        self.assertIn("action_lookup_logistics", reg.actions)
        self.assertIn("action_lookup_order_status", reg.actions)

    def test_05_engine_builder(self):
        """验证 build_engine 组装依赖图成功。"""
        engine = build_engine()
        self.assertIsNotNone(engine)
        self.assertIsNotNone(engine.task_handler)
        self.assertIsNotNone(engine.chitchat_handler)
        self.assertIsNotNone(engine.clarify_response)

    def test_06_turn_plan_validation_cases(self):
        """验证 13 个意图规划校验测试用例完全通过。"""
        flow_file = Path("customer/flow_config/user_flows.yml")
        catalog = FlowLoader().load(flow_file)
        validator = TurnPlanValidation()

        state = DialogueState(sender_id="u1001")
        state.tasks.active = TaskInstance(flow_id="refund_request", task_id="task_active_01")
        state.tasks.paused.append(TaskInstance(flow_id="order_status_query", task_id="task_paused_01"))

        cases = [
            ("未识别到任何意图", TurnPlan(), False, ClarifyReason.MISSING_TRACK),
            ("多个意图 (Task + Chitchat)", TurnPlan(task=TaskTurnPlan(commands=[StartFlowCommand(command="start_flow", flow="refund_request")]), chitchat=ChitchatTurnPlan()), False, ClarifyReason.MULTIPLE_TRACKS),
            ("闲聊意图", TurnPlan(chitchat=ChitchatTurnPlan()), True, None),
            ("知识检索意图", TurnPlan(knowledge=KnowledgeTurnPlan(intents=["faq_shipping"])), True, None),
            ("任务流程没有命令", TurnPlan(task=TaskTurnPlan(commands=[])), False, ClarifyReason.MISSING_TASK_COMMANDS),
            ("启动存在的 flow", TurnPlan(task=TaskTurnPlan(commands=[StartFlowCommand(command="start_flow", flow="refund_request")])), True, None),
            ("启动不存在的 flow", TurnPlan(task=TaskTurnPlan(commands=[StartFlowCommand(command="start_flow", flow="non_existent_flow")])), False, ClarifyReason.INVALID_TASK_COMMAND),
            ("恢复已暂停的任务", TurnPlan(task=TaskTurnPlan(commands=[ResumeTaskCommand(command="resume_task", task_id="task_paused_01")])), True, None),
            ("恢复不存在的任务", TurnPlan(task=TaskTurnPlan(commands=[ResumeTaskCommand(command="resume_task", task_id="unknown_task")])), False, ClarifyReason.INVALID_TASK_COMMAND),
            ("取消当前活跃任务", TurnPlan(task=TaskTurnPlan(commands=[CancelTaskCommand(command="cancel_task", task_id="task_active_01")])), True, None),
            ("取消暂停任务栈中的任务", TurnPlan(task=TaskTurnPlan(commands=[CancelTaskCommand(command="cancel_task", task_id="task_paused_01")])), True, None),
            ("取消不存在的任务", TurnPlan(task=TaskTurnPlan(commands=[CancelTaskCommand(command="cancel_task", task_id="unknown_task")])), False, ClarifyReason.INVALID_TASK_COMMAND),
            ("填充槽位命令", TurnPlan(task=TaskTurnPlan(commands=[SetSlotsCommand(command="set_slots", slots={"order_number": "123"})])), True, None),
        ]

        for desc, plan, expected_valid, expected_reason in cases:
            with self.subTest(msg=desc):
                res = validator.validate(plan, state, catalog)
                self.assertEqual(res.valid, expected_valid, f"{desc} valid mismatch")
                self.assertEqual(res.reason, expected_reason, f"{desc} reason mismatch")


class TestAsyncDialogueExecution(unittest.IsolatedAsyncioTestCase):
    """端到端多轮对话流程执行测试。"""

    async def test_multi_turn_dialogue(self):
        engine = build_engine()
        state = DialogueState(sender_id="test_user_e2e")
        mock_planner = AsyncMock()
        engine.turn_planner = mock_planner
        engine.task_handler.flow_executor.action_runner.run = AsyncMock(
            return_value=ActionResult(result={"order_status": "待发货", "order_summary": "包裹准备中"})
        )

        # Turn 1: Start flow
        mock_planner.plan.return_value = TurnPlan(
            task=TaskTurnPlan(commands=[StartFlowCommand(command="start_flow", flow="order_status_query")])
        )
        r1 = await engine.process_message(
            state, UserMessage(sender_id="test_user_e2e", message_id="m1", type=MessageType.TEXT, text="查订单")
        )
        self.assertTrue(any("订单号" in m.text for m in r1.messages), f"Turn 1 response failed: {[m.text for m in r1.messages]}")

        # Turn 2: Fill slot
        mock_planner.plan.return_value = TurnPlan(
            task=TaskTurnPlan(commands=[SetSlotsCommand(command="set_slots", slots={"order_number": "1101"})])
        )
        r2 = await engine.process_message(
            state, UserMessage(sender_id="test_user_e2e", message_id="m2", type=MessageType.TEXT, text="1101")
        )
        self.assertTrue(
            any("1101" in m.text and "待发货" in m.text for m in r2.messages),
            f"Turn 2 response failed: {[m.text for m in r2.messages]}",
        )


if __name__ == "__main__":
    unittest.main()
