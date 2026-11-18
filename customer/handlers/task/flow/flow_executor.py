from customer.domain.messages import UserMessage, BotMessage
from customer.domain.state import DialogueState
from customer.actions.action_runner import ActionRunner
from customer.handlers.task.flow.links import FlowStepLink, ConditionalLink, FallbackLink
from customer.handlers.task.flow.models import FlowCatalog, Flow
from customer.handlers.task.flow.steps import FlowStep, StartFlowStep, ResponseFlowStep, CollectSlotStep, ActionFlowStep, \
    EndFlowStep
from customer.handlers.task.response.task_response_render import ResponseRender

"""
根据 state 里面 active 的 step 开始推进流程实现
"""
class FlowExecutor:
    def __init__(self, response_render: ResponseRender,
                 action_runner: ActionRunner):
        self.response_render = response_render
        self.action_runner = action_runner

    async def execute(self, state: DialogueState,
                      user_message: UserMessage,
                      flow_catalog: FlowCatalog) -> list[BotMessage]:
        bot_messages: list[BotMessage] = []

        # 判断 state 是否存在活跃任务
        if not state.tasks.active:
            return bot_messages

        for _ in range(100):
            # 获取 step 对象
            flow_id = state.tasks.active.flow_id
            flow: Flow = flow_catalog.get_flow_by_id(flow_id)

            step_id = state.tasks.active.step_id
            step: FlowStep = flow.get_step_by_id(step_id)

            """
            start 步骤: 本身不做业务处理, 推进到下一步
            """
            # 判断 step 类型, 做不同的处理
            if isinstance(step, StartFlowStep):
                self._run_next_step(step, state)
                continue

            """
            response 步骤: 数据渲染, 把 action 步骤查询结果在这个步骤组装
            使用技术 jinja2
            """
            if isinstance(step, ResponseFlowStep):
                bot_message: BotMessage = await self.response_render.render(
                    template=step.template,
                    state=state,
                    user_message=user_message
                )
                bot_messages.append(bot_message)
                # 推进到下一步
                self._run_next_step(step, state)
                continue

            """
            collect 步骤: 收集槽位数据
            到 active 和 对象类型消息 找槽位数据
            都找不到, 等待用户输入
            """
            if isinstance(step, CollectSlotStep):
                # 返回 bool, true 表示有槽位数据推进到下一步
                #           false 表示没有槽位数据, 给用户返回提示信息
                is_collect: bool = self._get_collect_data(step, state, bot_messages)
                if is_collect:
                    self._run_next_step(step, state)
                    continue
                else:
                    return bot_messages

            """
            action 步骤: 执行具体业务方法, 调用中台接口方法得到结果
            使用技术 httpx
            """
            if isinstance(step, ActionFlowStep):
                action_result = await self.action_runner.run(
                    action_name=step.action,
                    state=state,
                )

                # 更新状态
                state.tasks.active.slots.update(action_result.result)

                # 数据渲染
                self._run_next_step(step, state)

                continue

            """
            end 步骤: 表示流程结束, 不需要到下一步, 清空 active 返回数据
            """
            if isinstance(step, EndFlowStep):
                state.tasks.active = None
                return bot_messages

    # 推进到下一步
    def _run_next_step(self, step: FlowStep, state: DialogueState):
        next_step_id = self._get_next_value(step.next, state)

        state.tasks.active.step_id = next_step_id

    def _get_next_value(self, step_link: list[FlowStepLink], state: DialogueState) -> str:
        # 无条件跳转, 返回 next 属性值
        if len(step_link) == 1:
            return step_link[0].target

        # 有条件跳转, 根据 if 判断 eval 方法, 返回不同值
        for link in step_link:
            # ConditionalLink 是 if then
            if isinstance(link, ConditionalLink):
                # 判断 if 里面表达式
                result = bool(eval(link.condition, {},
                          {"slots": state.tasks.active.slots}))
                if result: # 表达式成立
                    return link.target
                continue
            if isinstance(link, FallbackLink):
                return link.target


    # 收集槽位数据
    def _get_collect_data(
            self,
            step: CollectSlotStep,
            state: DialogueState,
            bot_messages: list[BotMessage],
    ) -> bool:
        """收集槽位数据，未收集到时添加追问提示。"""
        slot_name = step.slot_name

        # 1. 从 active 中获取，若已有值直接返回
        if state.tasks.active.slots.get(slot_name) is not None:
            return True

        # 2. 从对象类型消息获取并写入 active，成功后返回
        self.get_slot_data_from_object_message(step, state)
        if state.tasks.active.slots.get(slot_name) is not None:
            return True

        # 3. 仍未获取到，添加提示信息
        bot_messages.append(BotMessage(text=step.template.text))
        return False

    def get_slot_data_from_object_message(self, step: CollectSlotStep, state: DialogueState):
        # 对象消息放到 active 中
        if not state.shared.focused_object:
            return

        # 两种对象消息: 订单 order 和商品 product
        # type = order
        if step.slot_name == 'order_number' and state.shared.focused_object.type == 'order':
            order_number = state.shared.focused_object.id
            # 放入 active 中
            state.tasks.active.slots.update({'order_number': order_number})
            return

        # type = product
        if step.slot_name == 'product_id' and state.shared.focused_object.type == 'product':
            product_id = state.shared.focused_object.id
            # 放入 active 中
            state.tasks.active.slots.update({'product_id': product_id})
            return

