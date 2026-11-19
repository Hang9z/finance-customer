"""金融客服输入安全护栏（Prompt 注入防护与跨客户越权校验）."""
from dataclasses import dataclass
import re

_CUSTOMER_NO_RE = re.compile(r"\b(CUST?\d{4,})\b", re.IGNORECASE)

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"忽略(?:之前|以上|前面|所有|全部).{0,8}(?:指令|规则|提示|限制|约束)", re.IGNORECASE),
    re.compile(r"无视.{0,6}(?:系统|安全|风控).{0,6}(?:指令|规则|限制|提示)", re.IGNORECASE),
    re.compile(
        r"(?:输出|打印|显示|泄露|告诉我|返回).{0,10}(?:系统提示|提示词|system\s*prompt|密钥|秘钥|api[_\s]?key|数据库密码)",
        re.IGNORECASE,
    ),
    re.compile(r"假装你是.{0,12}(?:管理员|黑客|开发者|没有限制)", re.IGNORECASE),
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"(?:reveal|show|print|dump)\s+(?:your\s+)?(?:system\s+prompt|instructions|api\s+key)", re.IGNORECASE),
)

_INJECTION_REFUSAL = (
    "抱歉，我无法执行该指令。作为金融智能客服助手，我仅可为您提供账户查询、信贷办理、卡片挂失及工单服务等合规金融业务。"
)
_CROSS_CUSTOMER_REFUSAL = (
    "出于金融账户与客户隐私保护要求，您仅可查询及办理当前登录客户名下的业务，无法跨客户访问他人账户信息。"
)


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str | None = None
    refusal_message: str | None = None


def check_user_input_safety(text: str | None, sender_id: str) -> GuardrailResult:
    """检查用户输入是否存在 Prompt 注入/越狱或跨客户越权查询风险."""
    if not text:
        return GuardrailResult(allowed=True)

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return GuardrailResult(
                allowed=False,
                reason="prompt_injection",
                refusal_message=_INJECTION_REFUSAL,
            )

    current_customer = (sender_id or "").strip().upper()
    for match in _CUSTOMER_NO_RE.finditer(text):
        mentioned_customer = match.group(1).upper()
        if mentioned_customer != current_customer:
            return GuardrailResult(
                allowed=False,
                reason="cross_customer_access",
                refusal_message=_CROSS_CUSTOMER_REFUSAL,
            )

    return GuardrailResult(allowed=True)
