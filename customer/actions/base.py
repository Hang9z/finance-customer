"""定义数据模型与动作辅助工具."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from customer.domain.state import DialogueState


class Action(ABC):
    name: str = ""

    @abstractmethod
    async def run(self, state: DialogueState) -> "ActionResult":
        pass


@dataclass
class ActionResult:
    result: dict[str, Any] = field(default_factory=dict)


def get_active_slots(state: DialogueState) -> dict[str, Any]:
    """获取当前活跃任务的槽位字典."""
    return state.tasks.active.slots if state.tasks.active else {}


def resolve_customer_no(
    state: DialogueState,
    slots: dict[str, Any] | None = None,
) -> str | None:
    """从槽位或会话发送方标识中解析客户号."""
    active_slots = slots if slots is not None else get_active_slots(state)
    customer_no = active_slots.get("customer_no")
    if customer_no:
        return str(customer_no)
    if state.sender_id and str(state.sender_id).startswith(("CUS", "CUST")):
        return str(state.sender_id)
    return None
