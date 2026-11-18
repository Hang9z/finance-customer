"""
根据 commandProcessor 返回的 TaskEvent 生成不同中文提示
"""
from threading import current_thread

from customer.domain.messages import BotMessage
from customer.handlers.task.flow.models import FlowCatalog, Flow
from customer.handlers.task.response.task_event_type import TaskEvent, TaskStarted, TaskSwitched, TaskResumed, TaskCanceled


class TaskResponder:
    def __init__(self, flow_catalog: FlowCatalog):
        self.flow_catalog = flow_catalog

    async def respond(self, events: list[TaskEvent]) -> list[BotMessage]:
        messages: list[BotMessage] = []
        
        for event in events:
            messages.append(self.execute_event_data(event))
        return messages

    # 根据流程 id 获取流程名称
    def _get_flow_name(self, flow_id: str) -> str:
        flow_name = self.flow_catalog.get_flow_by_id(flow_id).name
        return flow_name


    # 根据 event 生成不同的中文提示
    def execute_event_data(self, event: TaskEvent) -> BotMessage:
        if isinstance(event, TaskStarted):
            flow_name = self._get_flow_name(event.task.flow_id)
            return BotMessage(text=f"好的, 现在开始执行{flow_name}")

        if isinstance(event, TaskSwitched):
            pre_flow_name = self._get_flow_name(event.previous.flow_id)
            current_flow_name = self._get_flow_name(event.current.flow_id)
            return BotMessage(text=f"好的, 现在把{pre_flow_name}暂停, 现在开始执行{current_flow_name}")

        if isinstance(event, TaskResumed):
            flow_name = self._get_flow_name(event.task.flow_id)
            return BotMessage(text=f"好的, 现在继续{flow_name}")

        if isinstance(event, TaskCanceled):
            flow_name = self._get_flow_name(event.task.flow_id)
            return BotMessage(text=f"好的, 现在取消{flow_name}")

        return BotMessage(text="哈哈")
