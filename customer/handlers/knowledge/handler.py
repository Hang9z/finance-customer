"""知识检索入口."""
import asyncio
import logging
from typing import Any

from customer.domain.messages import BotMessage, UserMessage
from customer.domain.state import DialogueState
from customer.handlers.knowledge.intents import KNOWLEDGE_INTENTS
from customer.handlers.knowledge.provider import KnowledgeChunk, KnowledgeProvider
from customer.handlers.knowledge.registry import KnowledgeProviderRegistry
from customer.handlers.knowledge.responder import KnowledgeResponder
from customer.security.masking import mask_sensitive_text

logger = logging.getLogger(__name__)


_SOURCE_PRIORITY = {
    "milvus": 0,
    "finance_api": 1,
    "web": 2,
    "local": 3,
}


def _build_citations(chunks: list[KnowledgeChunk]) -> list[dict[str, Any]] | None:
    """将命中的知识切片转换为前端可展示且经过脱敏的引用溯源列表."""
    ordered_chunks = sorted(
        chunks,
        key=lambda c: _SOURCE_PRIORITY.get(c.source_type, 9),
    )
    citations: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for chunk in ordered_chunks:
        if not chunk.source:
            continue
        snippet = mask_sensitive_text(chunk.content[:160].strip())
        if len(chunk.content.strip()) > 160:
            snippet = f"{snippet}..."
        dedup_key = (chunk.source, chunk.section, snippet[:40])
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        citations.append(
            {
                "source": chunk.source,
                "section": chunk.section,
                "score": round(chunk.score, 4) if chunk.score is not None else None,
                "sourceType": chunk.source_type,
                "url": chunk.url,
                "snippet": snippet,
            }
        )
    return citations or None


class KnowledgeHandler:
    def __init__(
        self,
        knowledge_registry: KnowledgeProviderRegistry,
        knowledge_responder: KnowledgeResponder,
    ):
        self.knowledge_registry = knowledge_registry
        self.knowledge_responder = knowledge_responder

    async def handle(
        self,
        knowledge_intents: list[str],
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[BotMessage]:
        provider_ids: list[str] = self.get_provider_ids(knowledge_intents)
        providers: list[KnowledgeProvider] = [
            p
            for pid in provider_ids
            if (p := self.knowledge_registry.get_provider(pid)) is not None
        ]

        results = await asyncio.gather(
            *(p.execute(state=state, user_message=user_message) for p in providers),
            return_exceptions=True,
        )
        final_result: list[KnowledgeChunk] = []
        for provider_obj, res in zip(providers, results):
            if isinstance(res, Exception):
                logger.warning("知识 Provider (%s) 执行异常: %s", provider_obj.provider_id, res)
            else:
                final_result.extend(res)

        bot_message: BotMessage = await self.knowledge_responder.respond(
            chunks=final_result,
            state=state,
            user_message=user_message,
        )
        citations = _build_citations(final_result)
        if citations and bot_message.citations is None:
            bot_message.citations = citations
        return [bot_message]

    def get_provider_ids(self, knowledge_intents: list[str]) -> list[str]:
        final_provider_ids: list[str] = []
        for intent in knowledge_intents:
            intent_meta = KNOWLEDGE_INTENTS.get(intent)
            if intent_meta is not None:
                final_provider_ids.extend(intent_meta.provider_ids)

        if not final_provider_ids:
            final_provider_ids.extend(["faq.default", "rag.default"])

        return list(dict.fromkeys(final_provider_ids))
