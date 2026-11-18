"""知识检索入口."""
from customer.domain.messages import BotMessage, UserMessage
from customer.domain.state import DialogueState
from customer.handlers.knowledge.intents import KNOWLEDGE_INTENTS
from customer.handlers.knowledge.provider import KnowledgeChunk, KnowledgeProvider
from customer.handlers.knowledge.registry import KnowledgeProviderRegistry
from customer.handlers.knowledge.responder import KnowledgeResponder


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

        final_result: list[KnowledgeChunk] = []
        for provider_id in provider_ids:
            provider_obj: KnowledgeProvider | None = self.knowledge_registry.get_provider(provider_id)
            if provider_obj is None:
                continue
            result: list[KnowledgeChunk] = await provider_obj.execute(
                state=state,
                user_message=user_message,
            )
            final_result.extend(result)

        bot_message: BotMessage = await self.knowledge_responder.respond(
            chunks=final_result,
            state=state,
            user_message=user_message,
        )
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
