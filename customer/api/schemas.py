from typing import Any

from pydantic import BaseModel


class ChatObject(BaseModel):
    type: str
    id: str
    title: str | None = None
    attributes: dict = {}


class ChatRequest(BaseModel):
    sender_id: str
    text: str | None = None
    object: ChatObject | None = None
    message_id: str | None = None


class ChatMessage(BaseModel):
    text: str | None = None
    object: ChatObject | None = None
    receipt: dict[str, Any] | None = None
    event: dict[str, Any] | None = None
    citations: list[dict[str, Any]] | None = None


class ChatResponse(BaseModel):
    sender_id: str
    message_id: str
    messages: list[ChatMessage]
    workflow_state: dict[str, Any] | None = None
    quick_replies: list[dict[str, str]] = []


class HistoryMessage(BaseModel):
    role: str # user/bot
    text: str | None = None
    object: ChatObject | None = None
    receipt: dict[str, Any] | None = None
    event: dict[str, Any] | None = None
    citations: list[dict[str, Any]] | None = None


class HistoryResponse(BaseModel):
    sender_id: str
    messages: list[HistoryMessage]
    workflow_state: dict[str, Any] | None = None
    quick_replies: list[dict[str, str]] = []


class SessionTokenRequest(BaseModel):
    customer_no: str


class SessionTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    customer_no: str
    expires_in: int


class CustomerAssetsResponse(BaseModel):
    customer_no: str
    customer_name: str | None = None
    risk_level: dict[str, Any] | None = None
    accounts: list[dict[str, Any]] = []
    credit_limits: list[dict[str, Any]] = []
    wealth_positions: list[dict[str, Any]] = []
    synced: bool = True


class RagStatusResponse(BaseModel):
    enabled: bool
    query_online: bool
    import_online: bool
    query_url: str
    chat_url: str
    import_url: str


class AdminTicketHandleRequest(BaseModel):
    ticket_status: str
    handle_result: str
    operator_no: str | None = None
    notify_customer: bool = True
    push_to_chat: bool = True


class CustomerTicketFeedbackRequest(BaseModel):
    customer_no: str
    confirm_status: str = "confirmed"
    satisfaction_score: int = 5
    feedback_content: str = "已确认处理结果"
