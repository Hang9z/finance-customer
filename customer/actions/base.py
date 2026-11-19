"""定义数据模型与动作辅助工具."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

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


def normalize_identifier(value: object) -> str:
    """去除银行卡号、账户号或业务单号中的空格与连字符."""
    return "".join(str(value).split()).replace("-", "")


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


def format_action_error(exc: Exception) -> str:
    """从 HTTPStatusError、超时/网络异常或普通异常中提取友好的中文错误描述."""
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            payload = exc.response.json()
            if isinstance(payload, dict):
                message = payload.get("message") or payload.get("detail")
                code = payload.get("code")
                if message and code:
                    return f"{message}（{code}）"
                if message:
                    return str(message)
        except Exception:
            pass
        return f"中台服务返回异常（HTTP {exc.response.status_code}）"
    if isinstance(exc, httpx.TimeoutException):
        return "中台服务响应超时，请稍后重试"
    if isinstance(exc, httpx.RequestError):
        detail = str(exc).strip()
        return f"中台服务连接异常（{detail}）" if detail else "中台服务连接异常，请稍后重试"
    detail = str(exc).strip()
    return detail or f"系统异常（{type(exc).__name__}）"
