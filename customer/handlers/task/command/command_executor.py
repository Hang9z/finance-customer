import uuid

from customer.domain.state import DialogueState, TaskInstance
from customer.plan.command import (
    Command,
    StartFlowCommand,
    SetSlotsCommand,
    ResumeTaskCommand,
    CancelTaskCommand,
)
from customer.handlers.task.flow.models import FlowCatalog
from customer.handlers.task.flow.steps import FlowStep
from customer.handlers.task.response.task_event_type import TaskEvent


class CommandExecutor:
    """
    负责执行意图识别生成的 Command，并更新 DialogueState 中的任务状态
    """

    async def update_task_state_by_command(
        self,
        commands: list[Command],
        state: DialogueState,
        flow_catalog: FlowCatalog,
    ) -> list[TaskEvent]:
        """
        执行 command, 根据 commands 更新 state 数据, 记录过程中的 TaskEvent
        :param commands: 意图识别结果列表
        :param state: 对话状态
        :param flow_catalog: 流程配置目录
        :return: 任务事件列表
        """
        events: list[TaskEvent] = []
        for command in commands:
            event: TaskEvent | None = self._execute_command(command, state, flow_catalog)
            if event:
                events.append(event)
        return events

    def _execute_command(
        self,
        command: Command,
        state: DialogueState,
        flow_catalog: FlowCatalog,
    ) -> TaskEvent | None:
        # {"command": "start_flow", "flow": "<flow_id>"}
        if isinstance(command, StartFlowCommand):
            flow_id = command.flow
            flow_def = flow_catalog.get_flow_by_id(flow_id)
            start_step: FlowStep = flow_def.get_start_step()

            task = TaskInstance(
                flow_id=flow_id,
                step_id=start_step.id,
                task_id=str(uuid.uuid4()),
            )
            return state.tasks.start_task(task)

        # {"command": "set_slots", "slots": {"slot_name": "<value>"}}
        if isinstance(command, SetSlotsCommand):
            if state.tasks.active is not None:
                state.tasks.active.slots.update(command.slots)
            return None

        # {"command": "resume_task", "task_id": "<task_id>"}
        if isinstance(command, ResumeTaskCommand):
            return state.tasks.resume_task(command.task_id)

        # {"command": "cancel_task", "task_id": "<task_id>"}
        if isinstance(command, CancelTaskCommand):
            return state.tasks.cancel_task(command.task_id)

        return None