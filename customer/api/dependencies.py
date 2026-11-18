from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from customer.engine import builder
from customer.engine.dialogue_engine import DialogueEngine
from customer.plan.turn_plan_validation import TurnPlanValidation
from customer.plan.turn_planner import TurnPlanner
from customer.repository.dialogue_repository import DialogueRepository
from customer.service.dialogue_service import DialogueService
from customer.handlers.task import task_handler
from customer.utils import database


# 创建获取数据库操作session对象方法
async def get_session():
    if database.async_session is None:
        database.init_db_engine()
    async with database.async_session() as session:
        yield session

# 创建repository对象
async def get_repository(session:AsyncSession=Depends(get_session)):
    # 注入操作数据库 session 会话对象
    return DialogueRepository(
        session=session,
    )

# 创建engine对象
async def get_engine():
    return builder.build_engine()

async def get_dialogue_service(
        repository:DialogueRepository=Depends(get_repository),
        engine:DialogueEngine=Depends(get_engine)) -> DialogueService:
    return DialogueService(
        repository=repository,
        engine=engine,
    )