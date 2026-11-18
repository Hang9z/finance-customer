from customer.domain.messages import UserMessage, BotMessage
from customer.domain.state import DialogueState
from customer.plan.command import Command
from customer.handlers.task.command.command_executor import CommandExecutor
from customer.handlers.task.flow.flow_executor import FlowExecutor
from customer.handlers.task.flow.models import FlowCatalog
from customer.handlers.task.response.task_event_type import TaskEvent
from customer.handlers.task.response.task_responder import TaskResponder


"""
 task任务流程对外入口
 调用 TaskHandler 三个组件
 update_task_state_by_command: 更新 state 状态
 task_responder: 生成中文提示
 flow_executor: 按步骤推进

 把最终结果合并, 返回给用户
"""
class TaskHandler:
    # 注入依赖关系
    def __init__(self, command_executor: CommandExecutor,
                task_responder: TaskResponder,
                flow_catalog: FlowCatalog,
                flow_executor: FlowExecutor):
        self.command_executor = command_executor
        self.task_responder = task_responder
        self.flow_catalog = flow_catalog
        self.flow_executor = flow_executor


    async def handle(self, commands: list[Command],
                      state: DialogueState,
                      user_message: UserMessage) -> list[BotMessage]:
        # 1. 调用 update_task_state_by_command 更新状态获得过程中得到的事件
        events: list[TaskEvent] = await self.command_executor.update_task_state_by_command(
            commands=commands,
            state=state,
            flow_catalog=self.flow_catalog
        )

        # 2. 根据 events 生成提示
        messages: list[BotMessage] = await self.task_responder.respond(
            events=events
        )

        # 3. 把这一步的结果和上一步 messages 合并
        bot_messages = await self.flow_executor.execute(
            state=state,
            user_message=user_message,
            flow_catalog=self.flow_catalog
        )

        messages.extend(bot_messages)
        return messages
