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
from customer.utils.observability import get_langchain_config


def _format_chunk_for_prompt(chunk: KnowledgeChunk) -> str:
    if chunk.source:
        section_part = f" / {chunk.section}" if chunk.section else ""
        return f"【来源：{chunk.source}{section_part}】\n{chunk.content}"
    return chunk.content


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
        turns = state.shared.sessions[-1].turns if state.shared.sessions else []

        result = await chain.ainvoke(
            input={
                "user_message":HistoryBuilder.render_user_message(user_message),
                "history":HistoryBuilder.build(turns),
                "knowledge_content":'\n'.join(
                    [_format_chunk_for_prompt(chunk) for chunk in chunks]
                )
            },
            config=get_langchain_config("knowledge_respond", ["knowledge"]),
        )
        return BotMessage(text=result)