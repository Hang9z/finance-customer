from dataclasses import dataclass, field
from customer.handlers.task.flow.steps import FlowStep, StartFlowStep

# 前端卡片/聚焦对象类型到流程槽位候选列表的统一映射
OBJECT_TYPE_SLOT_CANDIDATES: dict[str, tuple[str, ...]] = {
    "account": ("account_no", "card_no"),
    "card": ("card_no", "account_no"),
    "loan_product": ("product_code",),
    "loan_application": ("application_no", "related_no"),
    "wealth_product": ("product_code",),
    "transaction": ("related_no",),
    "ticket": ("ticket_no", "related_no"),
    "order": ("order_number",),
    "product": ("product_id", "product_code"),
}

@dataclass
class FlowSlot:
    name: str
    type: str = "any"
    label: str = ""
    description: str = ""

@dataclass
class Flow:
    id: str
    description: str = ""
    steps: list[FlowStep] = field(default_factory=list)
    slots: list[FlowSlot] = field(default_factory=list)
    name: str | None = None

    # 获取开始类型步骤数据
    def get_start_step(self)->StartFlowStep:
        for step in self.steps:
            # 判断 开始类型
            if isinstance(step, StartFlowStep):
                return step
        raise Exception("Flow not found")

    # 根据步骤id获取步骤对应数据
    def get_step_by_id(self, step_id)->FlowStep:
        for step in self.steps:
            if step.id == step_id:
                return step
        raise Exception("step not found")

@dataclass
class FlowCatalog:
    flows: dict[str, Flow] = field(default_factory=dict)
    slots: dict[str, FlowSlot] = field(default_factory=dict)

    # 根据流程id获取流程
    def get_flow_by_id(self, flow_id)->Flow:
        return self.flows[flow_id]


