from jinja2 import Template
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from customer.domain.messages import BotMessage, UserMessage
from customer.domain.state import DialogueState
from customer.prompts.history_builder import HistoryBuilder
from customer.handlers.task.response.task_response_template import ResponseTemplate, ResponseMode
from customer.utils.llm_client import llm


class ResponseRender:
    async def render(self,
                     template: ResponseTemplate,
                     state: DialogueState,
                     user_message: UserMessage) -> BotMessage | None:
        # mode=static yaml 是什么就返回什么
        if template.mode == ResponseMode.STATIC:
            # jinja2
            template = Template(template.text)
            render_text = template.render(slots=state.tasks.active.slots)
            return BotMessage(text=render_text)

        # 大模型对内容进行修改再返回
        if template.mode == ResponseMode.REPHRASE:
            template = Template(template.text)
            render_text = template.render(slots=state.tasks.active.slots)
            # 提示词模板
            prompt = PromptTemplate.from_template(
                template.prompt,template_format="jinja2"
            )
            chain = prompt | llm | StrOutputParser()
            result = await chain.ainvoke(
                {
                    "history": HistoryBuilder.build(state.shared.sessions[-1].turns),
                    "user_message": HistoryBuilder.render_user_message(user_message),
                    "current_response": render_text
                }
            )
            return BotMessage(text=result)

        # 直接让 llm 返回
        if template.mode == ResponseMode.GENERATE:
            return None
        return None