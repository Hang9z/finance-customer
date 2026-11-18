"""定义金融知识检索的意图范围与数据源映射."""
from dataclasses import dataclass, field


@dataclass
class KnowledgeIntent:
    id: str
    description: str
    provider_ids: list[str] = field(default_factory=list)
    requires_object: str | None = None


KNOWLEDGE_INTENTS: dict[str, KnowledgeIntent] = {
    "finance_product_consult": KnowledgeIntent(
        id="finance_product_consult",
        description="金融产品综合咨询（贷款、理财、基金、存款产品介绍与利率收益对比）",
        provider_ids=["api.finance_product", "faq.default"],
    ),
    "loan_product_info": KnowledgeIntent(
        id="loan_product_info",
        description="贷款产品咨询（贷款额度、利率区间、期限、还款方式及申请条件）",
        provider_ids=["api.finance_product", "faq.default"],
    ),
    "wealth_product_info": KnowledgeIntent(
        id="wealth_product_info",
        description="理财与基金产品咨询（预期收益率、风险等级、净值、起购及赎回规则）",
        provider_ids=["api.finance_product", "faq.default"],
    ),
    "interest_and_fee_policy": KnowledgeIntent(
        id="interest_and_fee_policy",
        description="利率、手续费标准及计息还款政策咨询（如转账手续费、提前还款政策、信用卡年费）",
        provider_ids=["faq.default", "rag.default"],
    ),
    "card_and_account_guide": KnowledgeIntent(
        id="card_and_account_guide",
        description="银行卡、信用卡权益与账户服务指南咨询（如金卡/白金卡权益对比、挂失补卡规则）",
        provider_ids=["faq.default", "rag.default"],
    ),
    "risk_and_compliance_notice": KnowledgeIntent(
        id="risk_and_compliance_notice",
        description="金融风险提示与业务规范咨询（如理财风险匹配、反诈安全须知、征信说明）",
        provider_ids=["faq.default", "rag.default"],
    ),
    "general_finance_info": KnowledgeIntent(
        id="general_finance_info",
        description="银行综合常见问题及通用金融服务咨询",
        provider_ids=["faq.default", "rag.default"],
    ),
}
