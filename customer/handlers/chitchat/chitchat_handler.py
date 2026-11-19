"""
 闲聊处理
"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from customer.domain.state import DialogueState
from customer.domain.messages import UserMessage, BotMessage
from customer.prompts.history_builder import HistoryBuilder
from customer.prompts.loader import load_prompt
from customer.utils.llm_client import llm
from customer.utils.observability import get_langchain_config


class ChitChatHandler:
    async def chitchat(self,
                       state: DialogueState,
                       user_message: UserMessage) -> list[BotMessage]:
        # 1. 构建提示词模板
        text = load_prompt("chitchat_respond")
        prompt = PromptTemplate.from_template(
            text,
            template_format="jinja2"
        )
        # 注意：StrOutputParser 必须实例化
        chain = prompt | llm | StrOutputParser()

        # 2. 获取历史轮次（加判空防守）
        turns = state.shared.sessions[-1].turns if state.shared.sessions else []
        history = HistoryBuilder.build(turns)

        # 3. ainvoke 直接传入入参字典，不要传 self
        result = await chain.ainvoke(
            {
                "history": history,
                "user_message": HistoryBuilder.render_user_message(user_message)
            },
            config=get_langchain_config("chitchat_respond", ["chitchat"]),
        )

        return [BotMessage(text=result)]