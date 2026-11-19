"""轻量 HS256 会话 Token 签发与鉴权模块."""
import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import HTTPException

from customer.config.config import settings


class AuthError(HTTPException):
    """鉴权失败异常."""


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def issue_session_token(
    customer_no: str,
    secret: str | None = None,
    ttl_seconds: int | None = None,
) -> dict[str, Any]:
    """为指定客户号签发 HS256 会话凭证."""
    clean_customer = (customer_no or "").strip()
    if not clean_customer:
        raise AuthError(status_code=400, detail="customer_no 不能为空")

    signing_secret = (secret or settings.auth_secret).encode("utf-8")
    ttl = ttl_seconds if ttl_seconds is not None else settings.auth_token_ttl_seconds
    now = int(time.time())

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": clean_customer,
        "iat": now,
        "exp": now + ttl,
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(signing_secret, signing_input, hashlib.sha256).digest()
    token = f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"

    return {
        "access_token": token,
        "token_type": "Bearer",
        "customer_no": clean_customer,
        "expires_in": ttl,
    }


def verify_session_token(token: str, secret: str | None = None) -> dict[str, Any]:
    """校验 HS256 会话凭证签名与有效期并返回声明载荷."""
    parts = (token or "").strip().split(".")
    if len(parts) != 3:
        raise AuthError(status_code=401, detail="无效的会话凭证格式")

    header_b64, payload_b64, sig_b64 = parts
    signing_secret = (secret or settings.auth_secret).encode("utf-8")
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = _b64url_encode(
        hmac.new(signing_secret, signing_input, hashlib.sha256).digest()
    )
    if not hmac.compare_digest(expected_sig, sig_b64):
        raise AuthError(status_code=401, detail="会话凭证签名无效")

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:
        raise AuthError(status_code=401, detail="会话凭证载荷损坏") from exc

    if not isinstance(payload, dict) or not payload.get("sub"):
        raise AuthError(status_code=401, detail="会话凭证缺少主体身份")

    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and time.time() > float(exp):
        raise AuthError(status_code=401, detail="会话凭证已过期，请重新签发")

    return payload


def validate_sender_authorization(sender_id: str, authorization: str | None) -> str:
    """校验请求头 Authorization 与目标 sender_id 是否一致."""
    clean_sender = (sender_id or "").strip()
    if not authorization:
        if settings.auth_required:
            raise AuthError(status_code=401, detail="缺少有效会话凭证")
        return clean_sender

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise AuthError(status_code=401, detail="Authorization 必须使用 Bearer 凭证")

    token = authorization[len(prefix) :].strip()
    payload = verify_session_token(token)
    subject = str(payload["sub"]).strip()
    if clean_sender and subject != clean_sender:
        raise HTTPException(
            status_code=403,
            detail="会话凭证与请求客户号不匹配，禁止跨客户访问",
        )
    return clean_sender or subject
