"""
 定义数据模型
"""
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



