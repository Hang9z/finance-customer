import asyncio
import sys
from pathlib import Path

# 保证以脚本形式直接运行当前文件时，能正常找到项目根目录模块
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from customer.config.config import settings

# 定义变量
engine: AsyncEngine | None = None
async_session: async_sessionmaker[AsyncSession] | None = None

# 初始化两个对象的方法
def init_db_engine():
    global engine,async_session
    # engine异步对象
    engine = create_async_engine(
        settings.database_url,
        echo=True,
    )
    # 通过session工厂创建session会话
    async_session = async_sessionmaker(
        engine,expire_on_commit=False
    )

# 关闭的异步方法
async def close_db_engine():
    await engine.dispose()

# 测试方法
async def test():
    init_db_engine()

    # 通过session工厂获取session对象，基于session里面engine数据库操作
    async with async_session()  as session:
        result = await session.execute(text("select 1"))
        print(result.fetchone())
    await close_db_engine()

if __name__ == '__main__':
    asyncio.run(test())