"""金融知识检索数据源 Provider 实现."""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from customer.clients.finance_client import finance_client
from customer.clients.rag_client import rag_client
from customer.config.config import settings
from customer.domain.messages import UserMessage
from customer.domain.state import DialogueState

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeChunk:
    content: str = ""
    source: str = ""
    section: str = ""
    score: float | None = None
    source_type: str = "local"
    url: str = ""


class KnowledgeProvider(ABC):
    provider_id: str = ""

    @abstractmethod
    async def execute(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[KnowledgeChunk]:
        pass


_FAQ_ENTRIES: list[tuple[tuple[str, ...], str]] = [
    (
        ("利率", "利息", "还款", "提前", "违约金", "等额", "贷款"),
        "【贷款利率与还款规则】我行消费信用贷与分期贷支持等额本息、等额本金及先息后本等还款方式，具体执行利率结合客户信用评估在产品利率区间内浮动。"
        "正常按期足额还款后可随时在手机银行申请提前结清；部分产品在放款 6 个月内提前结清可能收取剩余本金 1% 的手续费，具体以借款合同为准。",
    ),
    (
        ("手续费", "转账", "跨行", "取现", "费率"),
        "【转账与账户手续费】个人客户通过手机银行、网上银行办理境内本行及跨行实时转账暂免手续费；"
        "柜面跨行汇款按金额分段计费，单笔最高不超过 50 元。借记卡境内 ATM 跨行取现每月前 3 笔免收手续费，第 4 笔起按 2 元/笔收取。",
    ),
    (
        ("理财", "基金", "稳健", "风险", "收益", "赎回", "起购", "净值"),
        "【理财与基金产品说明】我行理财产品按风险等级划分为 R1（低风险/谨慎型）至 R5（高风险/激进型）。"
        "稳健投资可优先关注 R1/R2 等级固收类或现金管理类产品；理财产品为非保本浮动收益，过往业绩不代表未来表现。"
        "开放式产品通常支持 T+1 工作日申购确认及赎回资金到账（快速赎回单日限额 1 万元）。",
    ),
    (
        ("信用卡", "金卡", "白金", "年费", "权益", "免息期", "最低还款"),
        "【信用卡等级与还款规则】金卡基础额度通常为 1 万至 5 万元，首年免年费，当年刷卡满 6 笔免次年年费；"
        "白金卡基础额度通常为 5 万至 30 万元，享机场贵宾厅、道路救援及高额延误险等专属权益，主卡年费可通过积分或达标消费减免。"
        "信用卡免息还款期最长 56 天，最低还款额通常为当期账单金额的 10%。",
    ),
    (
        ("存款", "定期", "活期", "存期", "起存", "存单"),
        "【存款产品说明】人民币整存整取定期存款 50 元起存，提供 3 个月、6 个月、1 年、2 年、3 年、5 年期；"
        "大额存单 20 万元起存，支持按期付息及部分提前支取，提前支取部分按支取日挂牌活期利率计息。",
    ),
    (
        ("挂失", "丢失", "盗刷", "冻结", "安全"),
        "【卡片挂失与资金安全】发现卡片遗失或疑似盗刷，请立即通过智能客服、手机银行或致电 95555 办理紧急口头挂失，系统将即时止付账户。"
        "口头挂失后请携带本人有效身份证件前往网点办理正式挂失或补换新卡。",
    ),
]

_RAG_ENTRIES: list[tuple[tuple[str, ...], str]] = [
    (
        ("贷款", "审批", "授信", "征信", "材料", "条件"),
        "【信贷审批与合规规范】申请消费贷款需满足年满 22 至 60 周岁、信用记录良好且具备稳定收入来源。"
        "申请前需先持有有效授信额度；贷款资金严禁用于购房、股票、期货等投资性或监管禁止领域，逾期将按合同计收罚息并报送人民银行征信系统。",
    ),
    (
        ("风险", "测评", "合规", "反诈", "密码", "验证码"),
        "【金融消费风险与反诈提示】首次购买理财产品前需完成风险承受能力评估（有效期 1 年），不得向客户销售高于其风险等级的产品。"
        "我行客服人员绝不会索要您的银行卡密码、短信验证码或要求向所谓“安全账户”转账。",
    ),
    (
        ("投诉", "工单", "时效", "人工", "客服"),
        "【客服工单与投诉处理规范】提交投诉建议工单后，系统将生成唯一工单编号并由专席客服跟进核实，常规咨询与交易核查类工单在 24 小时内反馈进展，复杂争议将在 3 个工作日内给出处理方案。",
    ),
]


def _match_knowledge_entries(
    query: str,
    entries: list[tuple[tuple[str, ...], str]],
    fallback_limit: int = 2,
    source: str = "中州银行金融知识库",
    source_type: str = "local",
) -> list[KnowledgeChunk]:
    """按关键词命中权重筛选知识条目."""
    text = (query or "").strip()
    scored: list[tuple[int, str]] = []
    for keywords, content in entries:
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored.append((score, content))

    if not scored:
        return []

    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        KnowledgeChunk(content=content, source=source, score=float(hit_score), source_type=source_type)
        for hit_score, content in scored[:3]
    ]


class FinanceProductKnowledgeProvider(KnowledgeProvider):
    """金融产品知识检索 Provider（调用统一金融中台客户端）."""

    provider_id = "api.finance_product"

    async def execute(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[KnowledgeChunk]:
        text = user_message.text or ""
        focused = state.shared.focused_object

        payload: dict[str, object] = {}

        if focused and focused.id and focused.type in {"loan_product", "product"}:
            try:
                payload["focused_loan_product"] = await finance_client.get_loan_product_detail(focused.id)
            except Exception as exc:
                logger.warning("获取聚焦贷款产品详情失败 (%s): %s", focused.id, exc)

        want_loan = any(kw in text for kw in ("贷", "借", "分期", "利息", "额度"))
        want_wealth = any(kw in text for kw in ("理财", "基金", "稳健", "收益", "投资", "净值"))
        fetch_both = not want_loan and not want_wealth

        tasks = []
        task_keys: list[str] = []
        if want_loan or fetch_both:
            tasks.append(finance_client.get_loan_products(page_size=8))
            task_keys.append("loan_products")
        if want_wealth or fetch_both:
            tasks.append(finance_client.get_wealth_products(page_size=8))
            task_keys.append("wealth_products")

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for key, res in zip(task_keys, results):
            if isinstance(res, Exception):
                logger.warning("获取中台 %s 失败: %s", key, res)
            else:
                payload[key] = res

        if not payload:
            return [
                KnowledgeChunk(
                    content="暂时无法连接金融产品目录接口，请参考行内常规产品规则作答。",
                    source="中州银行产品兜底说明",
                    source_type="local",
                )
            ]

        return [
            KnowledgeChunk(
                content=json.dumps(payload, ensure_ascii=False),
                source="中州银行实时产品目录",
                section="中台在售产品与利率接口",
                source_type="finance_api",
            )
        ]


class FAQProvider(KnowledgeProvider):
    """金融业务 FAQ 知识检索 Provider."""

    provider_id = "faq.default"

    async def execute(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[KnowledgeChunk]:
        return _match_knowledge_entries(
            user_message.text or "",
            _FAQ_ENTRIES,
            fallback_limit=2,
            source="中州银行常见问答知识库",
            source_type="local",
        )


class RAGProvider(KnowledgeProvider):
    """金融合规政策与业务指南检索 Provider（优先调用金融智脑 RAG，离线时自动降级本地条目）."""

    provider_id = "rag.default"

    async def execute(
        self,
        state: DialogueState,
        user_message: UserMessage,
        enable_hyde: bool | None = None,
        enable_web: bool | None = None,
        skip_rewrite: bool | None = None,
    ) -> list[KnowledgeChunk]:
        query = (user_message.text or "").strip()
        if settings.rag_enabled and query:
            focused = state.shared.focused_object
            item_names = (
                [focused.title or focused.id]
                if focused
                and focused.type in {"finance_product", "knowledge_doc", "product"}
                and (focused.title or focused.id)
                else []
            )
            session_id = (
                state.shared.sessions[-1].session_id
                if state.shared.sessions
                else state.sender_id
            )
            should_skip_rewrite = bool(item_names) if skip_rewrite is None else skip_rewrite
            try:
                remote_items = await rag_client.retrieve(
                    query=query,
                    item_names=item_names,
                    enable_hyde=enable_hyde,
                    enable_web=enable_web,
                    skip_rewrite=should_skip_rewrite,
                    session_id=session_id,
                )
                chunks: list[KnowledgeChunk] = []
                for item in remote_items:
                    content = str(item.get("content") or "").strip()
                    if not content:
                        continue
                    source = str(
                        item.get("file_title")
                        or item.get("item_name")
                        or item.get("title")
                        or "金融智脑知识库"
                    ).strip()
                    section = str(item.get("parent_title") or item.get("title") or "").strip()
                    if section == source:
                        section = ""
                    raw_score = item.get("score")
                    chunks.append(
                        KnowledgeChunk(
                            content=content,
                            source=source,
                            section=section,
                            score=float(raw_score) if isinstance(raw_score, (int, float)) else None,
                            source_type=str(item.get("source_type") or "milvus"),
                            url=str(item.get("url") or ""),
                        )
                    )
                if chunks:
                    return chunks
            except Exception as exc:
                logger.warning("调用金融智脑 RAG 检索失败，将降级至本地合规知识库: %s", exc)

        return _match_knowledge_entries(
            query,
            _RAG_ENTRIES,
            fallback_limit=2,
            source="中州银行金融合规知识库",
            source_type="local",
        )
