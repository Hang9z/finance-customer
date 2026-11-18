"""金融中台 API 客户端.

统一封装对 finance-data 中台服务 (FastAPI) 的 HTTP 交互与鉴权逻辑。
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from customer.config.config import settings
from customer.utils.httpx_client import httpx_client

logger = logging.getLogger(__name__)


class FinanceClient:
    """金融业务中台 API 客户端."""

    def __init__(self, base_url: str | None = None, default_customer_no: str | None = None):
        self.base_url = (base_url or settings.finance_api_base_url).rstrip("/")
        self.default_customer_no = default_customer_no or getattr(
            settings, "finance_default_customer_no", "CUST00000001"
        )

    def _build_headers(self, customer_no: str | None = None) -> dict[str, str]:
        token = customer_no or self.default_customer_no
        return {
            "Authorization": f"Bearer {token}",
            "X-Request-Id": uuid.uuid4().hex,
            "Content-Type": "application/json",
        }

    # ==================== 1. 账户与交易 ====================

    async def get_account(self, account_no: str, customer_no: str | None = None) -> dict[str, Any]:
        """查询银行账户详情（含余额、可用余额、冻结金额、状态）."""
        url = f"{self.base_url}/accounts/{account_no}"
        headers = self._build_headers(customer_no)
        response = await httpx_client.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})

    async def get_transactions(
        self,
        account_no: str,
        start_date: str | None = None,
        end_date: str | None = None,
        page_no: int = 1,
        page_size: int = 20,
        customer_no: str | None = None,
    ) -> dict[str, Any]:
        """查询账户交易流水/明细."""
        url = f"{self.base_url}/accounts/{account_no}/transactions"
        params: dict[str, Any] = {"page_no": page_no, "page_size": page_size}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        headers = self._build_headers(customer_no)
        response = await httpx_client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})

    async def change_account_status(
        self,
        account_no: str,
        target_status: str,
        reason: str,
        request_no: str | None = None,
        customer_no: str | None = None,
    ) -> dict[str, Any]:
        """变更账户状态（如信用卡挂失、账户冻结等）."""
        url = f"{self.base_url}/accounts/{account_no}/status-changes"
        payload = {
            "request_no": request_no or uuid.uuid4().hex,
            "target_status": target_status,
            "reason": reason,
        }
        headers = self._build_headers(customer_no)
        response = await httpx_client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})

    # ==================== 2. 信贷申请 ====================

    async def apply_loan(
        self,
        customer_no: str,
        product_code: str,
        apply_amount: str | float,
        loan_term: int,
        loan_purpose: str = "日常消费",
        channel_code: str = "mobile_bank",
        request_no: str | None = None,
    ) -> dict[str, Any]:
        """提交贷款申请."""
        url = f"{self.base_url}/loan/applications"
        payload = {
            "request_no": request_no or uuid.uuid4().hex,
            "customer_no": customer_no or self.default_customer_no,
            "product_code": product_code,
            "apply_amount": f"{float(apply_amount):.2f}",
            "loan_term": int(loan_term),
            "loan_purpose": loan_purpose,
            "channel_code": channel_code,
        }
        headers = self._build_headers(customer_no)
        response = await httpx_client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})

    # ==================== 3. 运营与工单 ====================

    async def create_support_ticket(
        self,
        customer_no: str,
        category: str,
        description: str,
        related_no: str | None = None,
        channel_code: str = "mobile_bank",
        request_no: str | None = None,
    ) -> dict[str, Any]:
        """创建客服投诉/咨询工单."""
        url = f"{self.base_url}/support/tickets"
        payload = {
            "request_no": request_no or uuid.uuid4().hex,
            "customer_no": customer_no or self.default_customer_no,
            "category": category,
            "description": description,
            "channel_code": channel_code,
        }
        if related_no:
            payload["related_no"] = related_no

        headers = self._build_headers(customer_no)
        response = await httpx_client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})

    # ==================== 4. 金融产品与知识检索 ====================

    async def get_loan_products(self, page_no: int = 1, page_size: int = 20) -> list[dict[str, Any]]:
        """获取信贷产品列表及利率说明."""
        url = f"{self.base_url}/loan/products"
        headers = self._build_headers()
        response = await httpx_client.get(url, params={"page_no": page_no, "page_size": page_size}, headers=headers)
        response.raise_for_status()
        data = response.json().get("data", {})
        return data.get("items", []) if isinstance(data, dict) else data

    async def get_wealth_products(self, page_no: int = 1, page_size: int = 20) -> list[dict[str, Any]]:
        """获取理财/基金产品列表及收益说明."""
        url = f"{self.base_url}/wealth/products"
        headers = self._build_headers()
        response = await httpx_client.get(url, params={"page_no": page_no, "page_size": page_size}, headers=headers)
        response.raise_for_status()
        data = response.json().get("data", {})
        return data.get("items", []) if isinstance(data, dict) else data


finance_client = FinanceClient()
