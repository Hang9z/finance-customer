import sys
from pathlib import Path

# 保证以脚本形式直接运行时能正常找到项目根目录模块
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from customer.domain.state import DialogueState
from customer.plan.command import StartFlowCommand, ResumeTaskCommand, CancelTaskCommand, SetSlotsCommand
from customer.plan.turn_plan import TurnPlan, TurnPlanValidationResult, ClarifyReason, TaskTurnPlan
from customer.handlers.task.flow.models import FlowCatalog


"""
对 llm 意图识别结果进行校验
"""
class TurnPlanValidation:
    def validate(self, turn_plan:TurnPlan, state:DialogueState, flow_catalog:FlowCatalog):
        # 判断有几个意图
        active_list: list[str] = []

        if turn_plan.task is not None:
            active_list.append("task")

        if turn_plan.knowledge is not None:
            active_list.append("knowledge")

        if turn_plan.chitchat is not None:
            active_list.append("chitchat")

        # 未识别到任何意图
        if not active_list:
            return TurnPlanValidationResult(
                valid=False,
                reason=ClarifyReason.MISSING_TRACK
            )
        # 识别到多个意图
        if len(active_list) > 1:
            return TurnPlanValidationResult(
                valid=False,
                reason=ClarifyReason.MULTIPLE_TRACKS
            )
        
        # 识别到一个意图
        active_plan = active_list[0]
        if active_plan == "task":
            return self._validate_task(
                turn_plan.task,
                state,
                flow_catalog
            )
        if active_plan == "knowledge":
            return self._validate_knowledge()
        
        return TurnPlanValidationResult(valid=True)

    def _validate_task(self, task:TaskTurnPlan, state:DialogueState, flow_catalog:FlowCatalog) -> TurnPlanValidationResult:
            # 任务流程
            if not task.commands:
                return TurnPlanValidationResult(valid=False,
                                                reason=ClarifyReason.MISSING_TASK_COMMANDS)

            # 获取 commands 列表
            for command in task.commands:
                # 如果是 start_flow, 检查这个 flow 是否在 YAML 声明的 flow_catalog 中存在
                if isinstance(command, StartFlowCommand):
                    if command.flow not in flow_catalog.flows:
                        return TurnPlanValidationResult(valid=False, reason=ClarifyReason.INVALID_TASK_COMMAND)

                # 如果是 resume_task, 检查要恢复的 task_id 是否真的在暂停栈里面
                if isinstance(command, ResumeTaskCommand):
                    paused_ids = [t.task_id for t in state.tasks.paused]
                    if command.task_id not in paused_ids:
                        return TurnPlanValidationResult(valid=False, reason=ClarifyReason.INVALID_TASK_COMMAND)

                # cancel_task, 检查要取消的 task_id 是否存在
                if isinstance(command, CancelTaskCommand):
                    all_tasks_ids = [t.task_id for t in state.tasks.paused]
                    if state.tasks.active:
                        all_tasks_ids.append(state.tasks.active.task_id)
                    if command.task_id not in all_tasks_ids:
                        return TurnPlanValidationResult(valid=False, reason=ClarifyReason.INVALID_TASK_COMMAND)

            return TurnPlanValidationResult(valid=True)

    def _validate_knowledge(self):
        return TurnPlanValidationResult(valid=True)


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from customer.domain.state import TaskInstance
    from customer.plan.turn_plan import KnowledgeTurnPlan, ChitchatTurnPlan
    from customer.handlers.task.flow.loader import FlowLoader

    print("=" * 60)
    print("开始测试 TurnPlanValidation 校验逻辑...")
    print("=" * 60)

    # 1. 准备 flow_catalog 与测试 state
    flow_file = Path(__file__).resolve().parents[1] / "flow_config" / "user_flows.yml"
    flow_catalog = FlowLoader().load(flow_file)
    validator = TurnPlanValidation()

    state = DialogueState(sender_id="u1001")
    state.tasks.active = TaskInstance(flow_id="refund_request", task_id="task_active_01")
    state.tasks.paused.append(TaskInstance(flow_id="order_status_query", task_id="task_paused_01"))

    # 测试用例列表: (用例描述, turn_plan, 预期 valid, 预期 reason)
    test_cases = [
        # 1. 意图缺失
        (
            "测试未识别到任何意图",
            TurnPlan(),
            False,
            ClarifyReason.MISSING_TRACK,
        ),
        # 2. 多意图冲突
        (
            "测试识别到多个意图 (Task + Chitchat)",
            TurnPlan(task=TaskTurnPlan(), chitchat=ChitchatTurnPlan()),
            False,
            ClarifyReason.MULTIPLE_TRACKS,
        ),
        # 3. 闲聊意图通过
        (
            "测试闲聊意图 (合法)",
            TurnPlan(chitchat=ChitchatTurnPlan()),
            True,
            None,
        ),
        # 4. 知识问答意图通过
        (
            "测试知识检索意图 (合法)",
            TurnPlan(knowledge=KnowledgeTurnPlan(intents=["faq_shipping"])),
            True,
            None,
        ),
        # 5. 任务无命令
        (
            "测试任务流程没有命令 (空 commands)",
            TurnPlan(task=TaskTurnPlan(commands=[])),
            False,
            ClarifyReason.MISSING_TASK_COMMANDS,
        ),
        # 6. StartFlow 合法 flow
        (
            "测试启动存在的 flow (refund_request)",
            TurnPlan(task=TaskTurnPlan(commands=[StartFlowCommand(command="start_flow", flow="refund_request")])),
            True,
            None,
        ),
        # 7. StartFlow 不存在的 flow
        (
            "测试启动不存在的 flow (non_existent_flow)",
            TurnPlan(task=TaskTurnPlan(commands=[StartFlowCommand(command="start_flow", flow="non_existent_flow")])),
            False,
            ClarifyReason.INVALID_TASK_COMMAND,
        ),
        # 8. ResumeTask 恢复存在的暂停任务
        (
            "测试恢复已暂停的任务 (task_paused_01)",
            TurnPlan(task=TaskTurnPlan(commands=[ResumeTaskCommand(command="resume_task", task_id="task_paused_01")])),
            True,
            None,
        ),
        # 9. ResumeTask 恢复不存在的任务
        (
            "测试恢复不存在的任务 (unknown_task)",
            TurnPlan(task=TaskTurnPlan(commands=[ResumeTaskCommand(command="resume_task", task_id="unknown_task")])),
            False,
            ClarifyReason.INVALID_TASK_COMMAND,
        ),
        # 10. CancelTask 取消活跃任务
        (
            "测试取消当前活跃任务 (task_active_01)",
            TurnPlan(task=TaskTurnPlan(commands=[CancelTaskCommand(command="cancel_task", task_id="task_active_01")])),
            True,
            None,
        ),
        # 11. CancelTask 取消暂停中的任务
        (
            "测试取消暂停任务栈中的任务 (task_paused_01)",
            TurnPlan(task=TaskTurnPlan(commands=[CancelTaskCommand(command="cancel_task", task_id="task_paused_01")])),
            True,
            None,
        ),
        # 12. CancelTask 取消不存在的任务
        (
            "测试取消不存在的任务 (unknown_task)",
            TurnPlan(task=TaskTurnPlan(commands=[CancelTaskCommand(command="cancel_task", task_id="unknown_task")])),
            False,
            ClarifyReason.INVALID_TASK_COMMAND,
        ),
        # 13. SetSlotsCommand 合法设置槽位
        (
            "测试填充槽位命令 (set_slots)",
            TurnPlan(task=TaskTurnPlan(commands=[SetSlotsCommand(command="set_slots", slots={"order_number": "123"})])),
            True,
            None,
        ),
    ]

    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    all_passed = True
    for idx, (desc, plan, expected_valid, expected_reason) in enumerate(test_cases, 1):
        result = validator.validate(plan, state, flow_catalog)
        is_pass = (result.valid == expected_valid) and (result.reason == expected_reason)
        status = "[PASS]" if is_pass else "[FAIL]"
        if not is_pass:
            all_passed = False
        print(f"{status} 用例 {idx:02d}: {desc}")
        if not is_pass:
            print(f"       预期: valid={expected_valid}, reason={expected_reason}")
            print(f"       实际: valid={result.valid}, reason={result.reason}")

    print("=" * 60)
    if all_passed:
        print("全部 13 个测试用例均通过！TurnPlanValidation 校验逻辑完全正确。")
    else:
        print("存在未通过的用例，请检查逻辑。")
    print("=" * 60)