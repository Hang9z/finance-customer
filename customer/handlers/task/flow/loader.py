from pathlib import Path

import yaml

from customer.handlers.task.flow.models import FlowCatalog, FlowSlot, Flow
from customer.handlers.task.flow.steps import FlowStep, FlowStepType

"""
解析 yaml 文件，封装对应对象
"""
class FlowLoader:
    def load(self, path:Path) -> FlowCatalog:
        # 读取 yaml 文件所有内容，一大串字符串
        yaml_text = path.read_text(encoding='utf-8')
        # 字符串转字典
        flow_dict = yaml.safe_load(yaml_text)

        # dict[str, Any]
        # flows: dict[str, Flow]
        # slots: dict[str, FlowSlot]
        # 加载所有槽位数据
        slots: dict[str, FlowSlot] = self._load_slots(flow_dict["slots"])

        # 加载所有流程数据
        # 需要传入所有 槽位数据，因为流程中需要根据槽位名称获取其他信息
        flows: dict[str, Flow] = self._load_flows(flow_dict["flows"], slots)

        # 字典转对象
        return FlowCatalog(flows=flows, slots=slots)

    def _load_slots(self, slots_data: dict[str, dict]) -> dict[str, FlowSlot]:
        slots: dict[str, FlowSlot] = {}
        for slot_name, slot_data in slots_data.items():
            slots[slot_name] = FlowSlot(
                name=slot_name,
                **slot_data
            )

        return slots
    # 加载所有流程数据, 每个流程包含步骤数据和流程槽位数据
    def _load_flows(self, flows_data: dict[str, dict], slots: dict[str, FlowSlot]) -> dict[str, Flow]:
        flows: dict[str, Flow] = {}

        for flow_id, flow_data in flows_data.items():
            raw_steps = flow_data["steps"]

            flows[flow_id] = Flow(
                id=flow_id,
                name=flow_data["name"],
                description=flow_data["description"],
                steps=[FlowStep.from_dict(s) for s in raw_steps],
                slots=[slots[s["slot_name"]] for s in raw_steps if s["type"] == "collect"],
            )

        return flows



if __name__ == "__main__":
    loader = FlowLoader()
    path = Path(__file__).resolve().parents[3] / 'flow_config' / 'user_flows.yml'
    result = loader.load(path)
    print(result)