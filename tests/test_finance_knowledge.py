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

        result = await handler.handle(["unknown_intent"], state, msg)
        self.assertEqual(len(result), 1)
        self.assertIn("R1/R2", result[0].text)
        passed_chunks = handler.knowledge_responder.respond.await_args.kwargs["chunks"]
        self.assertTrue(len(passed_chunks) >= 2)


if __name__ == "__main__":
    unittest.main()
