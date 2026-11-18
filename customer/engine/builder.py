from pathlib import Path

from customer.handlers.chitchat.chitchat_handler import ChitChatHandler
from customer.handlers.clarify.clarify_response import ClarifyResponse
from customer.engine.dialogue_engine import DialogueEngine
from customer.handlers.knowledge.handler import KnowledgeHandler
from customer.handlers.knowledge.provider import ApiProductProvider, ApiOrderProvider, FAQProvider, RAGProvider
from customer.handlers.knowledge.registry import KnowledgeProviderRegistry
from customer.handlers.knowledge.responder import KnowledgeResponder
from customer.plan.turn_plan_validation import TurnPlanValidation
from customer.plan.turn_planner import TurnPlanner
from customer.handlers.task.actions import ActionRunner
from customer.handlers.task.actions.builder import registry_action
from customer.handlers.task.actions import ActionRegistry
from customer.handlers.task.command.command_executor import CommandExecutor
from customer.handlers.task.flow.flow_executor import FlowExecutor
from customer.handlers.task.flow.loader import FlowLoader
from customer.handlers.task.response.task_responder import TaskResponder
from customer.handlers.task.response.task_response_render import ResponseRender
from customer.handlers.task.task_handler import TaskHandler

path = Path(__file__).resolve().parents[1] / 'flow_config' / 'user_flows.yml'


"""
维护 engine 层的依赖关系
"""
def build_engine() -> DialogueEngine:

    # 1. 创建 FlowCatalog 对象
    flow_catalog = FlowLoader().load(path)

    # 2. 创建 TurnPlanner 对象
    turn_planner = TurnPlanner()

    # 3. 创建校验对象
    turn_plan_validation = TurnPlanValidation()

    # 4. 创建任务流程执行组件
    command_executor = CommandExecutor()
    task_responder = TaskResponder(
        flow_catalog=flow_catalog
    )

    # 5. 闲聊处理
    chitchat_handler = ChitChatHandler()

    # 6. 澄清回复处理
    clarify_response = ClarifyResponse()

    action_registry = ActionRegistry()
    registry_action(action_registry)
    action_runner = ActionRunner(registry=action_registry)
    response_render = ResponseRender()
    flow_executor = FlowExecutor(
        response_render=response_render,
        action_runner=action_runner,
    )

    task_handler = TaskHandler(
        command_executor=command_executor,
        task_responder=task_responder,
        flow_catalog=flow_catalog,
        flow_executor=flow_executor,
    )

    knowledge_handler = KnowledgeHandler(
        knowledge_responder=KnowledgeResponder(),
        knowledge_registry=KnowledgeProviderRegistry(
            provider_objects=[
                ApiProductProvider(),
                ApiOrderProvider(),
                FAQProvider(),
                RAGProvider()
            ]
        )
    )

    return DialogueEngine(
        turn_planner=turn_planner,
        turn_plan_validation=turn_plan_validation,
        task_handler=task_handler,
        chitchat_handler=chitchat_handler,
        clarify_response=clarify_response,
        knowledge_handler=knowledge_handler
    )