"""金融智脑 (finance_brain) RAG 检索客户端."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from customer.config.config import settings
import customer.utils.httpx_client as httpx_client_mod

logger = logging.getLogger(__name__)


class RagClient:
    """封装与 finance_brain 检索及文档导入服务的异步 HTTP 通信."""

    def __init__(
        self,
        base_url: str | None = None,
        import_base_url: str | None = None,
        timeout: float | None = None,
    ):
        self.base_url = (base_url or settings.rag_api_base_url).rstrip("/")
        self.import_base_url = (import_base_url or settings.rag_import_base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.rag_timeout_seconds

    @staticmethod
    def _http() -> httpx.AsyncClient:
        if httpx_client_mod.httpx_client is None:
            httpx_client_mod.init_httpx_client()
        assert httpx_client_mod.httpx_client is not None
        return httpx_client_mod.httpx_client

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        item_names: list[str] | None = None,
        enable_hyde: bool | None = None,
        enable_web: bool | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """调用 finance_brain `/api/v1/retrieve` 获取精排知识切片."""
        url = f"{self.base_url}/api/v1/retrieve"
        payload = {
            "query": query,
            "session_id": session_id,
            "top_k": top_k if top_k is not None else settings.rag_top_k,
            "item_names": item_names or [],
            "enable_hyde": settings.rag_enable_hyde if enable_hyde is None else enable_hyde,
            "enable_web": settings.rag_enable_web if enable_web is None else enable_web,
        }
        read_timeout = self.timeout if (self.timeout is not None and self.timeout > 0) else None
        req_timeout = httpx.Timeout(read_timeout, connect=3.0)
        response = await self._http().post(url, json=payload, timeout=req_timeout)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            chunks = data.get("chunks") or []
            return chunks if isinstance(chunks, list) else []
        return []

    async def _probe(self, url: str) -> bool:
        try:
            resp = await self._http().get(url, timeout=httpx.Timeout(2.0, connect=1.0))
            return resp.status_code == 200
        except Exception:
            return False

    async def check_health(self) -> dict[str, bool]:
        """并行检测金融智脑问答(8001)与文档导入(8002)服务健康状态."""
        query_ok, import_ok = await asyncio.gather(
            self._probe(f"{self.base_url}/health"),
            self._probe(f"{self.import_base_url}/health"),
        )
        return {
            "query_online": bool(query_ok),
            "import_online": bool(import_ok),
        }


rag_client = RagClient()
