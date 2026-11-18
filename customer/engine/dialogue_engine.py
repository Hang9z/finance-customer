import time
import uuid
from pathlib import Path

from customer.handlers.chitchat.chitchat_handler import ChitChatHandler
from customer.handlers.clarify.clarify_response import ClarifyResponse
from customer.domain.messages import UserMessage, ProcessResult, BotMessage, MessageType
from customer.domain.state import DialogueState, Session, Turn, TaskInstance, FocusedObject
from customer.handlers.knowledge.handler import KnowledgeHandler
from customer.handlers.task.command.command_executor import CommandExecutor
from customer.handlers.task.response.task_event_type import TaskEvent
from customer.plan.command import Command, StartFlowCommand, SetSlotsCommand, ResumeTaskCommand, CancelTaskCommand
from customer.plan.turn_plan import TurnPlan, TurnPlanValidationResult, ClarifyReason
from customer.plan.turn_plan_validation import TurnPlanValidation
from customer.plan.turn_planner import TurnPlanner
from customer.handlers.task.flow.loader import FlowLoader
from customer.handlers.task.flow.models import FlowCatalog
from customer.handlers.task.flow.steps import FlowStep, CollectSlotStep
from customer.handlers.task.task_handler import TaskHandler

# 默认会话超时时间 (单位：秒)
SESSION_TIMEOUT_SECONDS = 1800
# YAML 文件路径
path = Path(__file__).resolve().parents[1] / 'flow_config' / 'user_flows.yml'

"""
用于处理消息
"""
class DialogueEngine:

    def __init__(self, turn_planner: TurnPlanner,
                 turn_plan_validation: TurnPlanValidation,
                 task_handler: TaskHandler,
                 chitchat_handler: ChitChatHandler,
                 clarify_response: ClarifyResponse,
                 knowledge_handler: KnowledgeHandler):
        self.turn_planner = turn_planner
        self.turn_plan_validation = turn_plan_validation
        self.task_handler = task_handler
        self.chitchat_handler = chitchat_handler
        self.clarify_response = clarify_response or ClarifyResponse()
        self.knowledge_handler = knowledge_handler

    async def process_message(self, state: DialogueState, user_message: UserMessage)-> ProcessResult:
        # 准备会话 session
        self._prepare_current_session(state)

        # 判断消息类型: 文本和对象
        if user_message.type == MessageType.TEXT:
            bot_message: list[BotMessage] = await self._execute_text_message(state, user_message)
        else: # 对象消息
            bot_message: list[BotMessage] = await self._execute_object_message(state, user_message)

        # 提交本轮对象
        turn = Turn(
            turn_id=str(uuid.uuid4()),
            # 用户提问
            user_message=user_message,
            # 客服回复
            bot_message=bot_message or []
        )
        # 放到 state 里
        state.shared.sessions[-1].turns.append(turn)

        # 封装处理结果，返回给用户
        return ProcessResult(
            sender_id=user_message.sender_id,
            message_id=user_message.message_id,
            messages=bot_message or []
        )

    def _prepare_current_session(self, state):
        now = time.time()
        current_session: Session | None = None

        # 尝试获取列表中最后一个且未被关闭的 session
        if state.shared.sessions:
            last_session = state.shared.sessions[-1]
            if last_session.closed_at is None:
                current_session = last_session

        # 情况A：获取不到，说明是首次对话或者上一轮已被关闭，创建新 session
        if current_session is None:
            current_session = Session(
                session_id=str(uuid.uuid4()),
                started_at=now,
                last_activity_at=now
            )
            state.shared.sessions.append(current_session)
        else:
            # 情况 B：获取到了，判断是否超时
            if (now - current_session.last_activity_at) > SESSION_TIMEOUT_SECONDS:
                # 标记旧 session 关闭
                current_session.closed_at = now

                # 过期时清理旧任务状态
                state.tasks.active = None
                state.tasks.paused.clear()

                # 创建新的 session 并放入列表
                current_session = Session(
                    session_id=str(uuid.uuid4()),
                    started_at=now,
                    last_activity_at=now
                )
                state.shared.sessions.append(current_session)
            else:
                # 没有过期，更新最后活跃时间
                current_session.last_activity_at = now

        return current_session


    async def _execute_text_message(self, state, user_message):
        flow_catalog: FlowCatalog = FlowLoader().load(path)
        # 1 对文本消息做意图识别
        turn_plan: TurnPlan = await self.turn_planner.plan(
            state=state,
            user_message=user_message,
            flow_catalog=flow_catalog
        )

        # 2. 对意图识别结果校验
        validation_result: TurnPlanValidationResult = self.turn_plan_validation.validate(turn_plan=turn_plan,
                                           state=state,
                                           flow_catalog=flow_catalog)

        # 校验失败
        if not validation_result.valid:
            # 执行澄清回复组件
            return await self.clarify_response.clarify_response(
                reason=validation_result.reason,
                state=state,
                user_message=user_message
            )

        # 成功
        if turn_plan.task: # 执行任务
            messages: list[BotMessage] = await self.task_handler.handle(
                state=state,
                user_message=user_message,
                commands=turn_plan.task.commands
            )
            return messages or []

        if turn_plan.knowledge: # 知识检索
           messages:list[BotMessage] = await self.knowledge_handler.handle(
               knowledge_intents=turn_plan.knowledge.intents,
               state=state,
               user_message=user_message
           )
           return messages

        # 闲聊
        return await self.chitchat_handler.chitchat(state, user_message)

    async def _execute_object_message(self, state, user_message):
        if user_message.object:
            state.shared.focused_object = FocusedObject(
                type=user_message.object.type,
                id=user_message.object.id,
                title=user_message.object.title,
                attributes=user_message.object.attributes or {}
            )

            # 判断当前对象消息是否可以匹配活跃任务槽位
            if self._is_can_fit_slots(state):
                # 获取匹配的槽位名称 (例如: order -> order_number, product -> product_id)
                slot_name = "order_number" if user_message.object.type == "order" else "product_id"
                # 创建 commands
                command = SetSlotsCommand(
                    command="set_slots",
                    slots={slot_name: user_message.object.id}
                )

                # 执行任务
                return await self.task_handler.handle(
                    commands=[command],
                    state=state,
                    user_message=user_message
                )

            else:
                # 澄清回复
                return await self.clarify_response.clarify_response(
                    reason=ClarifyReason.OBJECT_REQUIRES_INTENT,
                    state=state,
                    user_message=user_message
                )

        return []

    def _is_can_fit_slots(self, state: DialogueState) -> bool:
        """
        判断当前对象消息是否可以匹配活跃任务所需的槽位
        """
        if not state.tasks.active or not state.shared.focused_object:
            return False

        obj_type = state.shared.focused_object.type
        flow_catalog = self.task_handler.flow_catalog
        flow = flow_catalog.get_flow_by_id(state.tasks.active.flow_id)

        # 1. 检查当前步骤是否为等待收集该槽位的 CollectSlotStep 且槽位未填
        step = flow.get_step_by_id(state.tasks.active.step_id)
        if isinstance(step, CollectSlotStep):
            if step.slot_name == "order_number" and obj_type == "order":
                return state.tasks.active.slots.get("order_number") is None
            if step.slot_name == "product_id" and obj_type == "product":
                return state.tasks.active.slots.get("product_id") is None

        # 2. 检查流程全部槽位中是否存在对应类型且尚未填写的槽位
        target_slot = "order_number" if obj_type == "order" else "product_id" if obj_type == "product" else None
        if target_slot:
            flow_slot_names = [s.name for s in flow.slots]
            if target_slot in flow_slot_names and state.tasks.active.slots.get(target_slot) is None:
                return True

        return False

