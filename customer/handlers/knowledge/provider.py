"""
 发送远程调用, 调用中台接口得到数据
"""
import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from customer.config.config import Settings, settings
from customer.domain.messages import UserMessage
from customer.domain.state import DialogueState
from customer.utils.httpx_client import httpx_client


# 定义结果
@dataclass
class KnowledgeChunk:
    content: str = ""

# 创建基类
class KnowledgeProvider(ABC):
    provider_id: str=""

    @abstractmethod
    async def execute(self, state:DialogueState,
                      user_message:UserMessage) -> list[KnowledgeChunk]:
        pass

# 商品信息咨询
class ApiProductProvider(KnowledgeProvider):
    provider_id = "api.product"

    async def execute(self, state:DialogueState,
                      user_message:UserMessage) -> list[KnowledgeChunk]:
        # 获取商品 id
        product_id = state.shared.focused_object.id

        url = f"{settings.commerce_api_base_url}/products/{product_id}"
        response = await httpx_client.get(url)
        data = response.json().get("data", {})
        chunk = json.dumps(data, ensure_ascii=False)
        return [KnowledgeChunk(content=chunk)]

# 订单信息咨询
class ApiOrderProvider(KnowledgeProvider):
    provider_id = "api.order"

    async def execute(self, state:DialogueState,
                      user_message:UserMessage) -> list[KnowledgeChunk]:
        order_id = state.shared.focused_object.id
        # 拼接远程调用路径
        order_url = f"{settings.commerce_api_base_url}/orders/{order_id}"
        logis_url = f"{settings.commerce_api_base_url}/orders/{order_id}/logistics"
        # 远程调用并行实现
        order_info, logis_info = await asyncio.gather(
            httpx_client.get(order_url),
            httpx_client.get(logis_url)
        )

        # list[KnowledgeChunk]
        chunk = json.dumps({
            "order_detail": order_info.json()["data"],
            "logis_detail": logis_info.json()["data"]
        }, ensure_ascii=False)
        return [KnowledgeChunk(content=chunk)]

#  faq
## 查询固定问题和固定答案
# 把这些问题和对应答案存储数据库里面，使用mysql，向量数据库
# 根据问题到数据库找到匹配问题，返回问题对应答案
class FAQProvider(KnowledgeProvider):
    provider_id = 'faq.default'

    async def execute(self, state: DialogueState,
                      user_message: UserMessage) -> list[KnowledgeChunk]:
        # TODO
        return [KnowledgeChunk(content="未检索到相关问题")]


# rag
## 调用智库里面查询接口得到结果
class RAGProvider(KnowledgeProvider):
    provider_id = 'rag.default'

    async def execute(self, state: DialogueState,
                      user_message: UserMessage) -> list[KnowledgeChunk]:
        # RAG知识库查询知识接口（TODO）
        return [KnowledgeChunk(content="未检索到相关信息")]