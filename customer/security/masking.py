"""金融敏感标识与文本脱敏工具."""
import re

_CARD_NUM_RE = re.compile(r"(?<![A-Za-z0-9*])(\d{16,19})(?![A-Za-z0-9*])")
_SPACED_CARD_RE = re.compile(r"(?<![A-Za-z0-9*])(\d{4}(?:[\s-]\d{4}){2,3}[\s-]\d{1,4})(?![A-Za-z0-9*])")
_ID_CARD_RE = re.compile(r"(?<![A-Za-z0-9*])([1-9]\d{5})\d{8}(\d{3}[0-9Xx])(?![A-Za-z0-9*])")
_PHONE_RE = re.compile(r"(?<![A-Za-z0-9*])(1[3-9]\d)\d{4}(\d{4})(?![A-Za-z0-9*])")
_ACC_NO_RE = re.compile(r"(?<![A-Za-z0-9*])(ACC)\d{4,}(\d{4})(?![A-Za-z0-9*])")
_MASKED_PAN_RE = re.compile(r"^(\d{4})\*+(\d{4})$")


def mask_identifier(value: object, spaced: bool = False) -> str:
    """对银行卡号与账户号进行脱敏展示，保留业务单号与 4 位短尾号可读性."""
    clean = "".join(str(value).split()).replace("-", "")
    if not clean:
        return ""

    # 已脱敏银行卡号按需格式化为空格分组
    masked_match = _MASKED_PAN_RE.match(clean)
    if masked_match:
        return (
            f"{masked_match.group(1)} **** **** {masked_match.group(2)}"
            if spaced
            else f"{masked_match.group(1)}****{masked_match.group(2)}"
        )

    # 纯数字且长度 >= 12 视为银行卡号 / 信用卡号
    if clean.isdigit() and len(clean) >= 12:
        return (
            f"{clean[:4]} **** **** {clean[-4:]}"
            if spaced
            else f"{clean[:4]}****{clean[-4:]}"
        )

    # 银行账户号 (ACC...) 连续脱敏展示，避免误拆为 4 位空格组
    if clean.startswith("ACC") and len(clean) >= 10:
        return f"{clean[:3]}****{clean[-4:]}"

    return clean


def mask_sensitive_text(text: str) -> str:
    """扫描并脱敏回复文本中的银行卡号、账户号、身份证号与手机号."""
    if not text:
        return text

    masked = _ID_CARD_RE.sub(r"\1********\2", text)
    masked = _SPACED_CARD_RE.sub(
        lambda m: mask_identifier(m.group(1), spaced=False),
        masked,
    )
    masked = _CARD_NUM_RE.sub(
        lambda m: f"{m.group(1)[:4]}****{m.group(1)[-4:]}",
        masked,
    )
    masked = _ACC_NO_RE.sub(r"\1****\2", masked)
    masked = _PHONE_RE.sub(r"\1****\2", masked)
    return masked
