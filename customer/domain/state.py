import uuid
from dataclasses import dataclass, field

from customer.domain.messages import UserMessage, BotMessage
from customer.handlers.task.response.task_event_type import TaskEvent, TaskSwitched, TaskRef, TaskStarted, TaskResumed, TaskCanceled


# 一轮对话，一个问题对应一个或者多个回答
@dataclass
class Turn:
    turn_id: str
    # 用户提问
    user_message: UserMessage
    # 客服回复
    bot_message: list[BotMessage]=field(default_factory=list)

# 表示一段连续的对话，可能会有多轮
@dataclass
class Session:
    # session的id，区别不同session
    session_id: str
    # session创建时间戳
    started_at: float
    # session最后一次活跃时间
    last_activity_at: float
    # 关闭时间
    closed_at: float | None = None
    # 每个session会话多轮对话
    turns:list[Turn]=field(default_factory=list)

# 保存在当前对话状态中的聚焦对象
@dataclass
class FocusedObject:
    # 对象类型
    type:str #  order   product
    # 对象的唯一标识
    id:str
    # 对象标题
    title:str | None=None
    # 对象携带的扩展属性
    attributes:dict=field(default_factory=dict)

# 三种能力都有数据：任务流程、知识问答、闲聊
@dataclass
class SharedState:
    # 当前聚焦的订单、商品等对象
    focused_object: FocusedObject | None = None
    # 当前用户的全部历史会话
    sessions: list[Session] = field(default_factory=list)


# 某个任务流程步骤相关数据
@dataclass
class TaskInstance:
    # 流程id，对应yaml文件  refund_request
    flow_id: str
    # 步骤id ,比如 start
    step_id: str | None = None
    # 当前任务id
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # task_id: str | None = None
    # 槽位数据字典  {order_number : a10098765}
    slots: dict= field(default_factory=dict)

    def get_task_ref(self) -> TaskRef:
        return TaskRef(
            task_id=self.task_id,
            flow_id=self.flow_id
        )

# 任务流程特有数据，流程步骤数据
@dataclass
class TaskState:
    # 当前正在运行（活跃）的任务
    active: TaskInstance | None = None
    # 中断（暂停）的任务
    paused: list[TaskInstance] = field(default_factory=list)

    def start_task(self, task) -> TaskEvent:
        if self.active:
            previous_task = self.active.get_task_ref()
            # 如果有, 把当前任务暂停, 新任务加入 active
            self.paused.append(self.active)
            self.active = task
            current_task = self.active.get_task_ref()
            return TaskSwitched(
                # 暂停任务
                previous=previous_task,
                # 当前活跃任务
                current=current_task
            )
        else:
            self.active = task
            return TaskStarted(
                task=self.active.get_task_ref()
            )

    # 恢复任务
    def resume_task(self, task_id) -> TaskEvent:
        be_resumed_task = None
        be_resumed_task_ref = None
        # 1. 从中断列表获取要恢复的任务
        for index, task in enumerate(self.paused):
            if task.task_id == task_id:
                be_resumed_task = self.paused.pop(index)
                be_resumed_task_ref = task.get_task_ref()
                break

        # 2. 判断恢复任务是否找到
        if be_resumed_task is None:
            raise Exception(f"Task not found in paused tasks")

        # 3. 如果找到恢复任务
        # 判断当前是否有活跃任务
        if self.active:
            previous_task = self.active.get_task_ref()

            self.paused.append(self.active)
            self.active = be_resumed_task

            return TaskSwitched(
                previous=previous_task,
                current=be_resumed_task_ref
            )
        else:
            self.active = be_resumed_task
            return TaskResumed(
                task=self.active.get_task_ref()
            )

    # 取消任务
    def cancel_task(self, task_id) -> TaskEvent:
        # 当前存在活跃任务并且是要取消的
        if self.active is not None and self.active.task_id == task_id:
            cancel_task = self.active.get_task_ref()
            # 取消
            self.active = None
            return TaskCanceled(
                task=cancel_task
            )
        # 中断列表找到取消任务
        else:
            for paused_task in self.paused:
                if paused_task.task_id == task_id:
                    cancel_task = paused_task.get_task_ref()
                    self.paused.remove(paused_task)
                    return TaskCanceled(
                        task=cancel_task
                    )

            raise Exception(f"Task not found in paused tasks")


@dataclass
class DialogueState:
    # 用户id
    sender_id: str
    # 三种能力都有数据：任务流程、知识问答、闲聊
    shared: SharedState=field(default_factory=SharedState)
    # 任务流程特有数据，流程步骤数据
    tasks: TaskState=field(default_factory=TaskState)