"""
 调用 llm, 对中台接口返回的数据进行修饰
"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from customer.domain.messages import BotMessage, UserMessage
from customer.domain.state import DialogueState
from customer.handlers.knowledge.provider import KnowledgeChunk
from customer.prompts.history_builder import HistoryBuilder
from customer.prompts.loader import load_prompt
from customer.utils.llm_client import llm


class KnowledgeResponder:
    async def respond(self,
                      chunks: list[KnowledgeChunk],
                      state:DialogueState,
                      user_message:UserMessage)->BotMessage:
        # 创建提示词模版
        text = load_prompt("knowledge_respond")
        prompt = PromptTemplate.from_template(
            text,template_format="jinja2",
        )

        chain = prompt | llm | StrOutputParser()

        result = await chain.ainvoke(
            input={
                "user_message":HistoryBuilder.render_user_message(user_message),
                "history":HistoryBuilder.build(
                    state.shared.sessions[-1].turns
                ),
                "knowledge_content":'\n'.join(
                    [  chunk.content
                        for chunk in chunks
                    ]
                )
            }
        )
        return BotMessage(text=result)