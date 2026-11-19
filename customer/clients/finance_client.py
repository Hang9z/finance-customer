"""金融中台 API 客户端.

统一封装对 finance-data 中台服务 (FastAPI) 的 HTTP 交互与鉴权逻辑。
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from customer.config.config import settings
import customer.utils.httpx_client as httpx_client_mod

logger = logging.getLogger(__name__)


class FinanceClient:
    """金融业务中台 API 客户端."""

    def __init__(
        self,
        base_url: str | None = None,
        default_customer_no: str | None = None,
        default_channel_code: str = "MOBILE_BANK",
        default_operator_no: str = "EMP000006",
    ):
        self.base_url = (base_url or settings.finance_api_base_url).rstrip("/")
        self.default_customer_no = default_customer_no or getattr(
            settings, "finance_default_customer_no", "CUS00000001"
        )
        self.default_channel_code = default_channel_code
        self.default_operator_no = default_operator_no

    @staticmethod
    def _http():
        if httpx_client_mod.httpx_client is None:
            httpx_client_mod.init_httpx_client()
        return httpx_client_mod.httpx_client

    @staticmethod
    def _normalize_identifier(value: str) -> str:
        """清洗银行卡号、账户号或业务单号中的空白和连字符."""
        return "".join(str(value).split()).replace("-", "")

    def _build_headers(
        self,
        customer_no: str | None = None,
        channel_code: str | None = None,
        operator_no: str | None = None,
    ) -> dict[str, str]:
        token = customer_no or self.default_customer_no
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Request-Id": uuid.uuid4().hex,
            "X-Channel-Code": channel_code or self.default_channel_code,
            "Content-Type": "application/json",
        }
        if operator_no:
            headers["X-Operator-No"] = operator_no
        return headers

    # ==================== 1. 账户与交易 ====================

    async def get_account(self, account_no: str, customer_no: str | None = None) -> dict[str, Any]:
        """查询银行账户详情（支持账户号、银行卡号及 4 位数字尾号）."""
        normalized_no = self._normalize_identifier(account_no)
        url = f"{self.base_url}/accounts/{normalized_no}"
        headers = self._build_headers(customer_no)
        response = await self._http().get(url, headers=headers)
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
        """查询账户交易流水/明细（支持账户号、银行卡号及 4 位数字尾号）."""
        normalized_no = self._normalize_identifier(account_no)
        url = f"{self.base_url}/accounts/{normalized_no}/transactions"
        params: dict[str, Any] = {"page_no": page_no, "page_size": page_size}
        if start_date:
            params["start_time"] = f"{start_date}T00:00:00" if len(start_date) == 10 else start_date
        if end_date:
            params["end_time"] = f"{end_date}T23:59:59" if len(end_date) == 10 else end_date

        headers = self._build_headers(customer_no)
        response = await self._http().get(url, params=params, headers=headers)
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
        """变更账户/关联银行卡状态（如信用卡挂失、账户冻结等）."""
        normalized_no = self._normalize_identifier(account_no)
        url = f"{self.base_url}/accounts/{normalized_no}/status-changes"
        payload = {
            "request_no": request_no or uuid.uuid4().hex,
            "target_status": target_status,
            "reason": reason,
        }
        headers = self._build_headers(customer_no)
        response = await self._http().post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})

    # ==================== 2. 信贷申请 ====================

    async def get_credit_limits(
        self,
        customer_no: str | None = None,
        product_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """查询客户名下授信额度列表."""
        resolved_customer = customer_no or self.default_customer_no
        url = f"{self.base_url}/customers/{resolved_customer}/credit-limits"
        params: dict[str, Any] = {}
        if product_code:
            params["product_code"] = product_code
        headers = self._build_headers(resolved_customer)
        response = await self._http().get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json().get("data", {})
        return data.get("list", []) if isinstance(data, dict) else data

    async def get_loan_product_detail(self, product_code: str) -> dict[str, Any]:
        """查询贷款产品详情."""
        url = f"{self.base_url}/loan/products/{product_code}"
        headers = self._build_headers()
        response = await self._http().get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})

    async def _resolve_limit_and_repayment(
        self,
        customer_no: str,
        product_code: str,
        apply_amount: float,
        limit_no: str | None,
        repayment_method: str | None,
    ) -> tuple[str, str]:
        """自动解析客户可用授信额度编号及产品还款方式."""
        resolved_limit = limit_no
        resolved_product_code = product_code
        if not resolved_limit:
            limits = await self.get_credit_limits(customer_no=customer_no, product_code=product_code)
            if not limits and product_code:
                limits = await self.get_credit_limits(customer_no=customer_no)
            if not limits:
                raise ValueError(f"客户 {customer_no} 暂无可用授信额度，请先办理授信申请")
            matched = next(
                (item for item in limits if float(item.get("available_limit_amount", 0)) >= apply_amount),
                limits[0],
            )
            resolved_limit = matched["limit_no"]
            resolved_product_code = matched.get("product_code") or product_code

        resolved_repayment = repayment_method
        if not resolved_repayment:
            try:
                detail = await self.get_loan_product_detail(resolved_product_code)
                product_info = detail.get("product_detail", {}) if isinstance(detail, dict) else {}
                resolved_repayment = product_info.get("repayment_method")
            except Exception as exc:
                logger.warning("获取贷款产品详情失败，将使用默认还款方式: %s", exc)
            resolved_repayment = resolved_repayment or "equal_principal_interest"

        return resolved_limit, resolved_repayment

    async def apply_loan(
        self,
        customer_no: str,
        product_code: str,
        apply_amount: str | float,
        loan_term: int,
        loan_purpose: str = "consume",
        channel_code: str = "MOBILE_BANK",
        request_no: str | None = None,
        limit_no: str | None = None,
        repayment_method: str | None = None,
    ) -> dict[str, Any]:
        """提交贷款申请."""
        resolved_customer = customer_no or self.default_customer_no
        amount_value = float(apply_amount)
        resolved_limit, resolved_repayment = await self._resolve_limit_and_repayment(
            customer_no=resolved_customer,
            product_code=product_code,
            apply_amount=amount_value,
            limit_no=limit_no,
            repayment_method=repayment_method,
        )

        url = f"{self.base_url}/loan/applications"
        payload = {
            "request_no": request_no or uuid.uuid4().hex,
            "customer_no": resolved_customer,
            "limit_no": resolved_limit,
            "apply_amount": f"{amount_value:.2f}",
            "apply_term_months": int(loan_term),
            "repayment_method": resolved_repayment,
            "loan_purpose": loan_purpose or "consume",
            "materials": [],
        }
        headers = self._build_headers(
            resolved_customer,
            channel_code=channel_code,
            operator_no=self.default_operator_no,
        )
        response = await self._http().post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})

    async def get_loan_application(
        self,
        application_no: str,
        customer_no: str | None = None,
    ) -> dict[str, Any]:
        """查询贷款申请进度与审批详情."""
        normalized_no = self._normalize_identifier(application_no)
        url = f"{self.base_url}/loan/applications/{normalized_no}"
        headers = self._build_headers(customer_no)
        response = await self._http().get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})

    # ==================== 3. 运营与工单 ====================

    async def create_support_ticket(
        self,
        customer_no: str,
        category: str,
        description: str,
        related_no: str | None = None,
        channel_code: str = "MOBILE_BANK",
        request_no: str | None = None,
    ) -> dict[str, Any]:
        """创建客服投诉/咨询工单."""
        resolved_customer = customer_no or self.default_customer_no
        url = f"{self.base_url}/support/tickets"
        content = description
        if related_no:
            content = f"{description}（关联业务单号：{related_no}）"
        title_snippet = description[:30] if description else "客服工单"
        payload = {
            "request_no": request_no or uuid.uuid4().hex,
            "customer_no": resolved_customer,
            "ticket_type": category,
            "ticket_title": f"[{category}] {title_snippet}",
            "ticket_content": content,
            "related_type": "none",
            "related_id": None,
        }

        headers = self._build_headers(
            resolved_customer,
            channel_code=channel_code,
            operator_no=self.default_operator_no,
        )
        response = await self._http().post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})

    async def get_support_ticket(
        self,
        ticket_no: str,
        customer_no: str | None = None,
    ) -> dict[str, Any]:
        """查询客服工单处理进度与详情."""
        normalized_no = self._normalize_identifier(ticket_no)
        url = f"{self.base_url}/support/tickets/{normalized_no}"
        headers = self._build_headers(customer_no)
        response = await self._http().get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})

    # ==================== 4. 金融产品与知识检索 ====================

    async def get_loan_products(self, page_no: int = 1, page_size: int = 20) -> list[dict[str, Any]]:
        """获取信贷产品列表及利率说明."""
        url = f"{self.base_url}/loan/products"
        headers = self._build_headers()
        response = await self._http().get(url, params={"page_no": page_no, "page_size": page_size}, headers=headers)
        response.raise_for_status()
        data = response.json().get("data", {})
        if isinstance(data, dict):
            return data.get("list") or data.get("items") or []
        return data

    async def get_wealth_products(self, page_no: int = 1, page_size: int = 20) -> list[dict[str, Any]]:
        """获取理财/基金产品列表及收益说明."""
        url = f"{self.base_url}/wealth/products"
        headers = self._build_headers()
        response = await self._http().get(url, params={"page_no": page_no, "page_size": page_size}, headers=headers)
        response.raise_for_status()
        data = response.json().get("data", {})
        if isinstance(data, dict):
            return data.get("list") or data.get("items") or []
        return data


finance_client = FinanceClient()
