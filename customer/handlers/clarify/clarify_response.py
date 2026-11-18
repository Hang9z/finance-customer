"""
 澄清回复
"""
import json
from dataclasses import asdict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from customer.domain.state import DialogueState
from customer.domain.messages import UserMessage, BotMessage
from customer.plan.turn_plan import ClarifyReason
from customer.prompts.history_builder import HistoryBuilder
from customer.prompts.loader import load_prompt
from customer.utils.llm_client import llm


class ClarifyResponse:
    async def clarify_response(self,
                               reason: ClarifyReason,
                               state: DialogueState,
                               user_message: UserMessage) -> list[BotMessage]:
        # 1. 根据失败原因, 生成基础中文提示
        text = self.build_reason(reason, state)

        # 2. 构建提示词模板
        prompt_text = load_prompt("clarify_respond")
        prompt = PromptTemplate.from_template(
            prompt_text,
            template_format="jinja2"
        )
        chain = prompt | llm | StrOutputParser()

        # 3. 提取历史记录与上下文
        turns = state.shared.sessions[-1].turns if state.shared.sessions else []
        history = HistoryBuilder.build(turns)
        user_msg_str = HistoryBuilder.render_user_message(user_message)
        focused_obj = (
            json.dumps(asdict(state.shared.focused_object), ensure_ascii=False)
            if state.shared.focused_object
            else None
        )

        # 4. 调用大模型改写生成更自然的澄清回复
        res = await chain.ainvoke(
            input={
                "reason": reason.value if hasattr(reason, "value") else str(reason),
                "clarify_message": text,
                "focused_object": focused_obj,
                "history": history,
                "user_message": user_msg_str
            }
        )

        return [BotMessage(text=res)]

    def build_reason(self, reason: ClarifyReason, state: DialogueState) -> str:
        reason_map = {
            ClarifyReason.MULTIPLE_TRACKS: "您的问题同时涉及多个业务需求，我一次只能处理一个，请问您想先处理哪一个？",
            ClarifyReason.MISSING_TRACK: "未能明确理解您的需求，请问您是想查询订单状态、查询物流、咨询商品还是申请退款？",
            ClarifyReason.MISSING_TASK_COMMANDS: "未识别到具体的任务操作指令，请详细说明您想办理的业务。",
            ClarifyReason.INVALID_TASK_COMMAND: "抱歉，无法执行该任务指令或未找到对应流程，请重新确认您的诉求。",
            ClarifyReason.MISSING_KNOWLEDGE_INTENT: "未能匹配到相关的帮助内容，请尝试更详细地描述您的问题。",
            ClarifyReason.UNKNOWN_KNOWLEDGE_INTENT: "未能找到相关的知识解答，请换个方式提问。",
            ClarifyReason.MISSING_FOCUSED_OBJECT: "当前操作需要指定商品或订单，请先提供对应的订单号或商品卡片。",
            ClarifyReason.OBJECT_REQUIRES_INTENT: "已收到您发送的卡片，请问需要针对它办理什么业务呢？",
        }
        return reason_map.get(reason, "抱歉，未能完全理解您的需求，请问有什么可以帮您的吗？")
