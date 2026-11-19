"""Langfuse 可观测性与 LangChain 链路追踪集成工具."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import logging
import os
from typing import Any, Iterator

from customer.config.config import settings

logger = logging.getLogger(__name__)

_current_langfuse_handler: ContextVar[Any | None] = ContextVar(
    "current_langfuse_handler",
    default=None,
)
_langfuse_initialized = False


def is_langfuse_configured() -> bool:
    """判断 Langfuse 是否启用且具备有效密钥."""
    return bool(
        settings.langfuse_enabled
        and settings.langfuse_secret_key
        and settings.langfuse_public_key
        and not settings.langfuse_secret_key.startswith("your_")
        and not settings.langfuse_public_key.startswith("your_")
    )


def init_langfuse() -> bool:
    """初始化 Langfuse 客户端并同步环境变量供 OTel/CallbackHandler 使用."""
    global _langfuse_initialized
    if not is_langfuse_configured():
        return False

    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_BASE_URL", settings.langfuse_base_url)

    if _langfuse_initialized:
        return True

    try:
        from langfuse import get_client

        get_client()
        _langfuse_initialized = True
        logger.info("Langfuse 可观测性已启用 (base_url=%s)", settings.langfuse_base_url)
        return True
    except Exception as exc:
        logger.warning("Langfuse 初始化失败，将降级为无追踪模式: %s", exc)
        return False


def flush_langfuse() -> None:
    """将缓存的 Trace 数据立即刷新至 Langfuse."""
    if not _langfuse_initialized:
        return
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception as exc:
        logger.debug("Langfuse flush 异常: %s", exc)


def shutdown_langfuse() -> None:
    """应用关闭时刷新并关闭 Langfuse 客户端."""
    if not _langfuse_initialized:
        return
    try:
        from langfuse import get_client

        client = get_client()
        client.flush()
        client.shutdown()
    except Exception as exc:
        logger.debug("Langfuse shutdown 异常: %s", exc)


def get_langchain_config(
    run_name: str,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """构建透传给 LangChain `ainvoke` 的回调与运行标识配置."""
    config: dict[str, Any] = {"run_name": run_name}
    if tags:
        config["tags"] = tags
    handler = _current_langfuse_handler.get()
    if handler is not None:
        config["callbacks"] = [handler]
    return config


@contextmanager
def trace_dialogue_turn(
    sender_id: str,
    session_id: str | None,
    user_input: Any,
) -> Iterator[Any | None]:
    """为单轮对话创建 Langfuse 根追踪 Span 并注入会话属性."""
    if not init_langfuse():
        yield None
        return

    try:
        from langfuse import get_client, propagate_attributes
        from langfuse.langchain import CallbackHandler

        client = get_client()
        with client.start_as_current_observation(
            as_type="span",
            name="finance_customer_turn",
            input=user_input,
        ) as span:
            with propagate_attributes(
                user_id=sender_id,
                session_id=session_id,
                trace_name="finance_customer_chat",
            ):
                handler = CallbackHandler()
                token = _current_langfuse_handler.set(handler)
                try:
                    yield span
                finally:
                    _current_langfuse_handler.reset(token)
    except Exception as exc:
        logger.warning("Langfuse 链路追踪上下文异常，已降级放行: %s", exc)
        yield None
