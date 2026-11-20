from collections.abc import Awaitable, Callable
import re
import time
import uuid
from pathlib import Path

from customer.config.config import settings
from customer.handlers.chitchat.chitchat_handler import ChitChatHandler
from customer.handlers.clarify.clarify_response import ClarifyResponse
from customer.domain.messages import UserMessage, ProcessResult, BotMessage, MessageType
from customer.domain.state import DialogueState, Session, Turn, FocusedObject
from customer.engine.protocol import build_workflow_snapshot
from customer.handlers.knowledge.handler import KnowledgeHandler
from customer.handlers.knowledge.provider import KnowledgeChunk
from customer.plan.command import SetSlotsCommand
from customer.plan.turn_plan import TurnPlan, TurnPlanValidationResult, ClarifyReason
from customer.plan.turn_plan_validation import TurnPlanValidation
from customer.plan.turn_planner import TurnPlanner
from customer.handlers.task.flow.loader import FlowLoader
from customer.handlers.task.flow.models import FlowCatalog, OBJECT_TYPE_SLOT_CANDIDATES
from customer.handlers.task.flow.steps import CollectSlotStep, ConfirmFlowStep
from customer.handlers.task.task_handler import TaskHandler
from customer.security.guardrails import check_user_input_safety
from customer.security.masking import mask_sensitive_text
from customer.utils.observability import trace_dialogue_turn

# 默认会话超时时间 (单位：秒)
SESSION_TIMEOUT_SECONDS = 1800
# YAML 文件路径
path = Path(__file__).resolve().parents[1] / 'flow_config' / 'user_flows.yml'

_CONFIRM_PUNCT_RE = re.compile(r"[\s，。！？!?,.\-：:]+")
_CONFIRM_TOKENS = {
    "确认",
    "确认办理",
    "确认提交",
    "确认挂失",
    "同意",
    "是的",
    "好",
    "好的",
    "确定",
    "yes",
    "ok",
    "confirm",
}
_CANCEL_TOKENS = {
    "取消",
    "取消操作",
    "不办了",
    "暂不办理",
    "放弃",
    "算了",
    "不要",
    "否",
    "no",
    "cancel",
}
_TRIVIAL_CHITCHAT_TOKENS = {
    "你好",
    "您好",
    "你好呀",
    "您好呀",
    "早上好",
    "下午好",
    "晚上好",
    "嗨",
    "hello",
    "hi",
    "谢谢",
    "非常感谢",
    "多谢",
    "感谢",
    "再见",
    "拜拜",
    "在吗",
    "你是谁",
    "你叫什么",
    "你叫什么名字",
}
_RAG_FALLBACK_MIN_SCORE = 0.35


def _should_probe_rag_before_chitchat(text: str | None) -> bool:
    """过滤纯寒暄和过短消息，避免无意义的远程向量检索."""
    raw = (text or "").strip()
    if len(raw) < 4:
        return False
    normalized = _CONFIRM_PUNCT_RE.sub("", raw).lower()
    return normalized not in _TRIVIAL_CHITCHAT_TOKENS

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
        self._flow_catalog: FlowCatalog | None = getattr(task_handler, "flow_catalog", None)

    def _get_flow_catalog(self) -> FlowCatalog:
        if self._flow_catalog is None:
            self._flow_catalog = FlowLoader().load(path)
        return self._flow_catalog

    async def process_message(
        self,
        state: DialogueState,
        user_message: UserMessage,
        on_stage: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> ProcessResult:
        # 准备会话 session
        current_session = self._prepare_current_session(state)
        flow_catalog = self._get_flow_catalog()
        trace_input = (
            mask_sensitive_text(user_message.text)
            if user_message.type == MessageType.TEXT and user_message.text
            else {
                "type": "object",
                "object_type": user_message.object.type if user_message.object else None,
                "object_id": user_message.object.id if user_message.object else None,
            }
        )

        with trace_dialogue_turn(
            sender_id=user_message.sender_id,
            session_id=current_session.session_id,
            user_input=trace_input,
        ) as trace_span:
            # 判断消息类型: 文本和对象
            if user_message.type == MessageType.TEXT:
                bot_message: list[BotMessage] = await self._execute_text_message(
                    state,
                    user_message,
                    flow_catalog=flow_catalog,
                    on_stage=on_stage,
                )
            else:  # 对象消息
                bot_message = await self._execute_object_message(state, user_message, on_stage=on_stage)

            # 统一对非事件文本做敏感信息脱敏
            sanitized_messages = bot_message or []
            for msg in sanitized_messages:
                if msg.text and msg.event is None:
                    msg.text = mask_sensitive_text(msg.text)

            # 提交本轮对象
            turn = Turn(
                turn_id=str(uuid.uuid4()),
                # 用户提问
                user_message=user_message,
                # 客服回复
                bot_message=sanitized_messages,
            )
            # 放到 state 里
            state.shared.sessions[-1].turns.append(turn)

            workflow_state, quick_replies = build_workflow_snapshot(state, flow_catalog)

            if trace_span is not None:
                try:
                    trace_span.update(
                        output={
                            "replies": [m.text for m in sanitized_messages if m.text],
                            "active_flow": (workflow_state.get("active") or {}).get("flowId"),
                        }
                    )
                except Exception:
                    pass

            # 封装处理结果，返回给用户
            return ProcessResult(
                sender_id=user_message.sender_id,
                message_id=user_message.message_id,
                messages=sanitized_messages,
                workflow_state=workflow_state,
                quick_replies=quick_replies,
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


    @staticmethod
    def _normalize_confirm_input(text: str | None) -> str:
        return _CONFIRM_PUNCT_RE.sub("", (text or "")).lower()

    def _try_handle_confirmation_gate(
        self,
        state: DialogueState,
        user_message: UserMessage,
        flow_catalog: FlowCatalog,
    ) -> tuple[str, ConfirmFlowStep] | None:
        """检查是否处于高风险二次确认门禁，并识别明确的确认或取消答复."""
        active = state.tasks.active
        if not active or not active.step_id:
            return None
        flow = flow_catalog.flows.get(active.flow_id)
        if not flow:
            return None
        step = flow.get_step_by_id(active.step_id)
        if not isinstance(step, ConfirmFlowStep):
            return None

        normalized = self._normalize_confirm_input(user_message.text)
        if normalized in _CONFIRM_TOKENS:
            return ("confirm", step)
        if normalized in _CANCEL_TOKENS:
            return ("cancel", step)
        return None

    async def _execute_text_message(
        self,
        state: DialogueState,
        user_message: UserMessage,
        flow_catalog: FlowCatalog | None = None,
        on_stage: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> list[BotMessage]:
        catalog = flow_catalog or self._get_flow_catalog()

        # 0. 输入安全护栏（拦截 Prompt 注入与跨客户越权）
        guardrail = check_user_input_safety(user_message.text, user_message.sender_id)
        if not guardrail.allowed:
            return [BotMessage(text=guardrail.refusal_message or "抱歉，您的请求未通过安全合规校验。")]

        # 0.5 确定性高危操作二次确认门禁
        gate = self._try_handle_confirmation_gate(state, user_message, catalog)
        if gate is not None:
            decision, confirm_step = gate
            flow = catalog.get_flow_by_id(state.tasks.active.flow_id)
            flow_name = flow.name or flow.id
            if decision == "confirm":
                state.tasks.active.slots[confirm_step.confirm_slot] = True
                return await self.task_handler.flow_executor.execute(
                    state=state,
                    user_message=user_message,
                    flow_catalog=catalog,
                    on_stage=on_stage,
                )
            state.tasks.active = None
            raw_cancel = f"好的, 现在取消{flow_name}"
            return [
                BotMessage(
                    text=raw_cancel,
                    event={"kind": "cancel", "flow": flow_name, "rawText": raw_cancel},
                ),
                BotMessage(text=confirm_step.cancel_message),
            ]

        if on_stage is not None:
            await on_stage("planning", "正在理解您的业务意图...")

        # 1 对文本消息做意图识别
        turn_plan: TurnPlan = await self.turn_planner.plan(
            state=state,
            user_message=user_message,
            flow_catalog=catalog
        )

        # 2. 对意图识别结果校验
        validation_result: TurnPlanValidationResult = self.turn_plan_validation.validate(
            turn_plan=turn_plan,
            state=state,
            flow_catalog=catalog
        )

        # 校验失败
        if not validation_result.valid:
            if on_stage is not None:
                await on_stage("responding", "正在整理回复...")
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
                commands=turn_plan.task.commands,
                on_stage=on_stage,
            )
            return messages or []

        if turn_plan.knowledge: # 知识检索
            if on_stage is not None:
                await on_stage("knowledge", "正在检索金融知识与产品...")
            messages = await self.knowledge_handler.handle(
                knowledge_intents=turn_plan.knowledge.intents,
                state=state,
                user_message=user_message
            )
            return messages

        # 闲聊前先对非寒暄文本做一次高置信度 RAG 兜底，避免知识库已入库文档被误判为闲聊
        if settings.rag_enabled and _should_probe_rag_before_chitchat(user_message.text):
            remote_hits = await self._probe_remote_rag_chunks(state, user_message)
            if remote_hits:
                if on_stage is not None:
                    await on_stage("knowledge", "正在检索金融知识与产品...")
                return await self.knowledge_handler.handle(
                    knowledge_intents=["general_finance_info"],
                    state=state,
                    user_message=user_message,
                    prefetched_chunks=remote_hits,
                )

        # 闲聊
        if on_stage is not None:
            await on_stage("responding", "正在整理回复...")
        return await self.chitchat_handler.chitchat(state, user_message)

    async def _probe_remote_rag_chunks(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[KnowledgeChunk]:
        """当意图规划未命中知识分支时，探测远端 RAG 是否存在高相关切片."""
        rag_provider = self.knowledge_handler.knowledge_registry.get_provider("rag.default")
        if rag_provider is None:
            return []
        try:
            chunks = await rag_provider.execute(
                state=state,
                user_message=user_message,
                enable_hyde=False,
                enable_web=False,
                skip_rewrite=True,
            )
        except Exception:
            return []
        return [
            chunk
            for chunk in chunks
            if chunk.source_type != "local"
            and (chunk.score is None or chunk.score >= _RAG_FALLBACK_MIN_SCORE)
        ]

    async def _execute_object_message(
        self,
        state: DialogueState,
        user_message: UserMessage,
        on_stage: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> list[BotMessage]:
        if user_message.object:
            state.shared.focused_object = FocusedObject(
                type=user_message.object.type,
                id=user_message.object.id,
                title=user_message.object.title,
                attributes=user_message.object.attributes or {}
            )

            # 判断当前对象消息是否可以匹配活跃任务槽位
            slot_name = self._resolve_fit_slot(state)
            if slot_name:
                command = SetSlotsCommand(
                    command="set_slots",
                    slots={slot_name: user_message.object.id}
                )
                return await self.task_handler.handle(
                    commands=[command],
                    state=state,
                    user_message=user_message,
                    on_stage=on_stage,
                )

            if on_stage is not None:
                await on_stage("responding", "正在整理回复...")
            return await self.clarify_response.clarify_response(
                reason=ClarifyReason.OBJECT_REQUIRES_INTENT,
                state=state,
                user_message=user_message
            )

        return []

    def _is_can_fit_slots(self, state: DialogueState) -> bool:
        """判断当前对象消息是否可以匹配活跃任务所需的槽位."""
        return self._resolve_fit_slot(state) is not None

    def _resolve_fit_slot(self, state: DialogueState) -> str | None:
        """根据聚焦对象类型与当前任务上下文匹配待填充槽位名."""
        if not state.tasks.active or not state.shared.focused_object:
            return None

        obj_type = state.shared.focused_object.type
        candidates = OBJECT_TYPE_SLOT_CANDIDATES.get(obj_type, ())
        if not candidates:
            return None

        flow_catalog = self.task_handler.flow_catalog
        flow = flow_catalog.get_flow_by_id(state.tasks.active.flow_id)

        # 1. 优先检查当前等待收集的 CollectSlotStep
        step = flow.get_step_by_id(state.tasks.active.step_id)
        if isinstance(step, CollectSlotStep) and step.slot_name in candidates:
            if state.tasks.active.slots.get(step.slot_name) is None:
                return step.slot_name

        # 2. 检查流程全部 collect 槽位中首个匹配且尚未填写的槽位
        flow_slot_names = {s.name for s in flow.slots}
        for slot_name in candidates:
            if slot_name in flow_slot_names and state.tasks.active.slots.get(slot_name) is None:
                return slot_name

        return None

