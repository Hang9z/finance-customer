"""金融知识检索模块单元测试."""
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from customer.domain.messages import BotMessage, MessageType, UserMessage
from customer.domain.state import DialogueState, FocusedObject
from customer.engine.builder import build_engine
from customer.handlers.knowledge.intents import KNOWLEDGE_INTENTS
from customer.handlers.knowledge.provider import (
    FAQProvider,
    FinanceProductKnowledgeProvider,
    RAGProvider,
)


class TestFinanceKnowledgeSetup(unittest.TestCase):
    """验证金融知识意图与引擎注册 Provider 一致性."""

    def test_all_knowledge_intents_mapped_to_registered_providers(self):
        engine = build_engine()
        registry = engine.knowledge_handler.knowledge_registry

        self.assertIn("api.finance_product", registry.providers_dict)
        self.assertIn("faq.default", registry.providers_dict)
        self.assertIn("rag.default", registry.providers_dict)
        self.assertNotIn("api.product", registry.providers_dict)
        self.assertNotIn("api.order", registry.providers_dict)

        for intent_id, meta in KNOWLEDGE_INTENTS.items():
            self.assertTrue(meta.provider_ids, f"Intent {intent_id} missing provider_ids")
            for pid in meta.provider_ids:
                self.assertIsNotNone(
                    registry.get_provider(pid),
                    f"Intent {intent_id} references unregistered provider {pid}",
                )


class TestFinanceKnowledgeProviders(unittest.IsolatedAsyncioTestCase):
    """验证金融产品检索、FAQ 与合规指南检索行为."""

    async def test_finance_product_provider_fetches_wealth_and_focused_loan(self):
        provider = FinanceProductKnowledgeProvider()
        state = DialogueState(sender_id="CUST00000001")
        state.shared.focused_object = FocusedObject(type="loan_product", id="LOAN_CONSUMER_STD")
        msg = UserMessage(
            sender_id="CUST00000001",
            message_id="m1",
            type=MessageType.TEXT,
            text="有没有稳健的理财产品和消费贷？",
        )

        with (
            patch(
                "customer.handlers.knowledge.provider.finance_client.get_loan_product_detail",
                new=AsyncMock(return_value={"product_detail": {"product_code": "LOAN_CONSUMER_STD"}}),
            ),
            patch(
                "customer.handlers.knowledge.provider.finance_client.get_loan_products",
                new=AsyncMock(return_value=[{"product_code": "LOAN_CONSUMER_STD"}]),
            ),
            patch(
                "customer.handlers.knowledge.provider.finance_client.get_wealth_products",
                new=AsyncMock(return_value=[{"product_code": "WLT_STEADY_01", "risk_level": "R2"}]),
            ),
        ):
            chunks = await provider.execute(state, msg)

        self.assertEqual(len(chunks), 1)
        self.assertIn("LOAN_CONSUMER_STD", chunks[0].content)
        self.assertIn("WLT_STEADY_01", chunks[0].content)

    async def test_finance_product_provider_degrades_on_partial_failure(self):
        provider = FinanceProductKnowledgeProvider()
        state = DialogueState(sender_id="CUST00000001")
        msg = UserMessage(
            sender_id="CUST00000001",
            message_id="m2",
            type=MessageType.TEXT,
            text="介绍一下金融产品",
        )

        with (
            patch(
                "customer.handlers.knowledge.provider.finance_client.get_loan_products",
                new=AsyncMock(side_effect=RuntimeError("timeout")),
            ),
            patch(
                "customer.handlers.knowledge.provider.finance_client.get_wealth_products",
                new=AsyncMock(return_value=[{"product_code": "WLT_01"}]),
            ),
        ):
            chunks = await provider.execute(state, msg)

        self.assertEqual(len(chunks), 1)
        self.assertIn("WLT_01", chunks[0].content)

    async def test_faq_and_rag_providers_match_financial_topics(self):
        faq = FAQProvider()
        rag = RAGProvider()
        state = DialogueState(sender_id="CUST00000001")

        msg_card = UserMessage(
            sender_id="CUST00000001",
            message_id="m3",
            type=MessageType.TEXT,
            text="信用卡金卡和白金卡年费权益有什么区别？",
        )
        faq_chunks = await faq.execute(state, msg_card)
        self.assertTrue(any("白金卡" in c.content for c in faq_chunks))

        msg_risk = UserMessage(
            sender_id="CUST00000001",
            message_id="m4",
            type=MessageType.TEXT,
            text="购买理财产品需要做风险测评吗？",
        )
        with patch(
            "customer.handlers.knowledge.provider.rag_client.retrieve",
            new=AsyncMock(return_value=[]),
        ):
            rag_chunks = await rag.execute(state, msg_risk)
        self.assertTrue(any("风险承受能力评估" in c.content for c in rag_chunks))

    async def test_knowledge_handler_handles_unknown_intent_gracefully(self):
        engine = build_engine()
        handler = engine.knowledge_handler
        handler.knowledge_responder.respond = AsyncMock(
            return_value=BotMessage(text="稳健型理财可关注 R1/R2 等级产品。")
        )

        state = DialogueState(sender_id="CUST00000001")
        msg = UserMessage(
            sender_id="CUST00000001",
            message_id="m5",
            type=MessageType.TEXT,
            text="有什么理财推荐？",
        )

        with patch(
            "customer.handlers.knowledge.provider.rag_client.retrieve",
            new=AsyncMock(return_value=[]),
        ):
            result = await handler.handle(["unknown_intent"], state, msg)
        self.assertEqual(len(result), 1)
        self.assertIn("R1/R2", result[0].text)
        passed_chunks = handler.knowledge_responder.respond.await_args.kwargs["chunks"]
        self.assertTrue(len(passed_chunks) >= 2)

    async def test_rag_provider_uses_remote_finance_brain_and_returns_citations(self):
        engine = build_engine()
        handler = engine.knowledge_handler
        handler.knowledge_responder.respond = AsyncMock(
            return_value=BotMessage(text="根据消费贷管理办法，利率范围 3.6%-7.2%。")
        )
        state = DialogueState(sender_id="CUS00000001")
        msg = UserMessage(
            sender_id="CUS00000001",
            message_id="m6",
            type=MessageType.TEXT,
            text="消费贷提前还款违约金怎么算？",
        )

        with patch(
            "customer.handlers.knowledge.provider.rag_client.retrieve",
            new=AsyncMock(
                return_value=[
                    {
                        "chunk_id": "fb_1",
                        "content": "放款 6 个月内提前结清收取剩余本金 1% 手续费，关联账户 ACC0000000001。",
                        "file_title": "个人消费贷款管理办法.pdf",
                        "parent_title": "第五章 提前还款",
                        "source_type": "milvus",
                        "score": 0.92,
                    }
                ]
            ),
        ):
            result = await handler.handle(["interest_and_fee_policy"], state, msg)

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].citations)
        cit = result[0].citations[0]
        self.assertEqual(cit["source"], "个人消费贷款管理办法.pdf")
        self.assertEqual(cit["section"], "第五章 提前还款")
        self.assertEqual(cit["sourceType"], "milvus")
        self.assertEqual(cit["score"], 0.92)
        self.assertIn("ACC****0001", cit["snippet"])

    async def test_rag_provider_falls_back_when_remote_unavailable(self):
        rag = RAGProvider()
        state = DialogueState(sender_id="CUS00000001")
        msg = UserMessage(
            sender_id="CUS00000001",
            message_id="m7",
            type=MessageType.TEXT,
            text="消费贷征信和风险测评规范",
        )

        with patch(
            "customer.handlers.knowledge.provider.rag_client.retrieve",
            new=AsyncMock(side_effect=RuntimeError("Connection refused")),
        ):
            chunks = await rag.execute(state, msg)

        self.assertTrue(len(chunks) >= 1)
        self.assertEqual(chunks[0].source_type, "local")
        self.assertEqual(chunks[0].source, "中州银行金融合规知识库")

    def test_all_knowledge_intents_include_rag_provider(self):
        for intent_id, intent_meta in KNOWLEDGE_INTENTS.items():
            self.assertIn(
                "rag.default",
                intent_meta.provider_ids,
                f"KnowledgeIntent {intent_id} 必须包含 rag.default",
            )

    async def test_chitchat_turn_with_high_score_rag_hit_promotes_to_knowledge(self):
        from customer.plan.turn_plan import TurnPlan

        engine = build_engine()
        engine.turn_planner.plan = AsyncMock(return_value=TurnPlan(chitchat={}))
        engine.chitchat_handler.chitchat = AsyncMock(
            return_value=[BotMessage(text="should not reach chitchat")]
        )
        engine.knowledge_handler.knowledge_responder.respond = AsyncMock(
            return_value=BotMessage(text="2026年第一季度营业收入53,909,252,220.51元。")
        )
        state = DialogueState(sender_id="CUS00000001")
        msg = UserMessage(
            sender_id="CUS00000001",
            message_id="m8",
            type=MessageType.TEXT,
            text="贵州茅台酒股份有限公司2026年第一季度营业收入和净利润分别是多少？",
        )

        with patch(
            "customer.handlers.knowledge.provider.rag_client.retrieve",
            new=AsyncMock(
                return_value=[
                    {
                        "chunk_id": "mt_1",
                        "content": "2026年第一季度实现营业收入53,909,252,220.51元。",
                        "file_title": "贵州茅台酒股份有限公司2026 年第一季度报告",
                        "parent_title": "合并利润表",
                        "source_type": "milvus",
                        "score": 0.9999,
                    }
                ]
            ),
        ) as mock_retrieve:
            result = await engine.process_message(state, msg)

        self.assertEqual(mock_retrieve.await_count, 1)
        engine.chitchat_handler.chitchat.assert_not_awaited()
        self.assertEqual(len(result.messages), 1)
        self.assertIn("53,909,252,220.51", result.messages[0].text)
        self.assertTrue(result.messages[0].citations)
        self.assertEqual(
            result.messages[0].citations[0]["source"],
            "贵州茅台酒股份有限公司2026 年第一季度报告",
        )


if __name__ == "__main__":
    unittest.main()
