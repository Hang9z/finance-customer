"""
创建fastapi对象
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from customer.api.chat_router import chat_router
from customer.utils.database import init_db_engine, close_db_engine
from customer.utils.httpx_client import init_httpx_client, close_httpx_client
from customer.utils.observability import init_langfuse, shutdown_langfuse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 数据库使用对象初始化操作
    init_db_engine()
    # 远程调用对象初始化操作
    init_httpx_client()
    # Langfuse 可观测性初始化
    init_langfuse()
    yield
    shutdown_langfuse()
    await close_db_engine()
    await close_httpx_client()

app = FastAPI(lifespan=lifespan)
app.include_router(chat_router)