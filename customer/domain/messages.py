from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# 1. 最先：被最多类引用的枚举
class MessageType(Enum):
    TEXT = "text"
    OBJECT = "object"


# 2. 其次：被 UserMessage 和 BotMessage 共同引用
@dataclass
class MessageObject:
    type: str
    id: str
    title: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


# 3. UserMessage 依赖上面两个，必须排在它们后面
@dataclass
class UserMessage:
    sender_id: str
    message_id: str
    type: MessageType              # 注意：没默认值，必须排在 text 前面
    text: str | None = None
    object: MessageObject | None = None


# 4. BotMessage 只依赖 MessageObject
@dataclass
class BotMessage:
    text: str | None = None
    object: MessageObject | None = None


# 5. ProcessResult 依赖 BotMessage，必须最后
@dataclass
class ProcessResult:
    sender_id: str
    message_id: str
    # 客服回复
    messages: list[BotMessage]     # 这里也不用引号了
