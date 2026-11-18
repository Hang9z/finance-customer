import json
import sys
from dataclasses import asdict
from pathlib import Path

from customer.handlers.knowledge.intents import KNOWLEDGE_INTENTS

# 保证以脚本形式直接运行时能正常找到项目根目录模块
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from customer.domain.messages import UserMessage
from customer.domain.state import DialogueState, Turn
from customer.prompts.history_builder import HistoryBuilder
from customer.prompts.loader import load_prompt
from customer.plan.turn_plan import TurnPlan
from customer.handlers.task.flow.models import FlowCatalog, Flow
from customer.utils.llm_client import llm


"""
根据用户文本消息调用 llm 进行意图识别
"""
class TurnPlanner:

    async def plan(self, state: DialogueState, user_message: UserMessage, flow_catalog: FlowCatalog) -> TurnPlan:
        # 1. 创建提示词模板
        prompt_text = load_prompt("turn_plan")
        prompt = PromptTemplate.from_template(
            prompt_text,
            template_format="jinja2"
        )

        # 2. 创建调用链
        chain = prompt | llm | JsonOutputParser()

        # 获取 user_message 渲染文本
        rendered_user_message = HistoryBuilder.render_user_message(user_message)
        # 获取 conversation_history 历史 (防空判断)
        turns: list[Turn] = state.shared.sessions[-1].turns if state.shared.sessions else []
        conversation_history = HistoryBuilder.build(turns)

        # 获取 focused_object_json (防 None 判断)
        focused_object_json = (
            json.dumps(asdict(state.shared.focused_object), ensure_ascii=False)
            if state.shared.focused_object
            else "null"
        )

        # 获取所有流程数据 flows_json
        flows: dict[str, Flow] = flow_catalog.flows
        # 把流程里所有步骤部分数据去掉（llm 只做意图识别，没有推进步骤）
        flows_data = [
            {k: v for k, v in asdict(flow).items() if k != "steps"}
            for flow in flows.values()
        ]
        flows_json = json.dumps(flows_data, ensure_ascii=False, indent=2)

        # 获取任务状态 task_state_json
        task_state_json = json.dumps(asdict(state.tasks), ensure_ascii=False, indent=2)

        # 知识库意图列表 (预留)
        knowledge_intents_json = json.dumps(
            [   {
                "id": intent.id,
                "description": intent.description
            }
                for intent in KNOWLEDGE_INTENTS.values()
            ],ensure_ascii= False
        )

        # 3. 调用方法执行, 传入提示词模板所需的所有字段
        result = await chain.ainvoke(input={
            "user_message": rendered_user_message,
            "conversation_history": conversation_history,
            "focused_object_json": focused_object_json,
            "flows_json": flows_json,
            "task_state_json": task_state_json,
            "knowledge_intents_json": knowledge_intents_json,
        })

        # 4. 把 llm 返回的 json 结构转为对象
        return TurnPlan.from_dict(result)


if __name__ == "__main__":
    import asyncio
    from customer.domain.messages import MessageType
    from customer.domain.state import Session
    from customer.handlers.task.flow.loader import FlowLoader

    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    async def main():
        print("=" * 60)
        print("开始测试 TurnPlanner (调用 LLM 规划用户意图)...")
        print("=" * 60)

        # 1. 加载流程配置
        flow_file = Path(__file__).resolve().parents[1] / "flow_config" / "user_flows.yml"
        flow_catalog = FlowLoader().load(flow_file)
        planner = TurnPlanner()

        # 准备测试 State
        state = DialogueState(sender_id="CUST00000001")
        state.shared.sessions.append(Session(session_id="s1001", started_at=0, last_activity_at=0))

        # 测试用例 1: 业务任务意图 (账户余额查询)
        msg1 = UserMessage(
            sender_id="CUST00000001",
            message_id="m1",
            type=MessageType.TEXT,
            text="帮我查一下账户 ACC0000000001 的余额"
        )
        print("\n[测试用例 1 - 账户余额查询]")
        print("用户输入:", msg1.text)
        plan1 = await planner.plan(state, msg1, flow_catalog)
        print("LLM 规划结果:")
        print(f"  task: {plan1.task}")
        print(f"  knowledge: {plan1.knowledge}")
        print(f"  chitchat: {plan1.chitchat}")

        # 测试用例 2: 闲聊意图
        msg2 = UserMessage(
            sender_id="CUST00000001",
            message_id="m2",
            type=MessageType.TEXT,
            text="你好，今天天气真不错"
        )
        print("\n[测试用例 2 - 闲聊]")
        print("用户输入:", msg2.text)
        plan2 = await planner.plan(state, msg2, flow_catalog)
        print("LLM 规划结果:")
        print(f"  task: {plan2.task}")
        print(f"  knowledge: {plan2.knowledge}")
        print(f"  chitchat: {plan2.chitchat}")

        # 测试用例 3: 业务任务意图 (贷款申请)
        msg3 = UserMessage(
            sender_id="CUST00000001",
            message_id="m3",
            type=MessageType.TEXT,
            text="我想申请消费贷款"
        )
        print("\n[测试用例 3 - 贷款申请]")
        print("用户输入:", msg3.text)
        plan3 = await planner.plan(state, msg3, flow_catalog)
        print("LLM 规划结果:")
        print(f"  task: {plan3.task}")
        print(f"  knowledge: {plan3.knowledge}")
        print(f"  chitchat: {plan3.chitchat}")

        print("\n" + "=" * 60)
        print("TurnPlanner 测试执行完毕！")
        print("=" * 60)

    asyncio.run(main())
