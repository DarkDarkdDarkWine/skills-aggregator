from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import logging

from .config import config
from .models import Base

logger = logging.getLogger(__name__)


# 创建异步数据库引擎
def create_database_engine():
    """创建数据库引擎"""
    db_config = config.database

    # 使用 asyncpg 作为 PostgreSQL 的异步驱动
    engine = create_async_engine(
        db_config.url.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )

    return engine


def get_sessionmaker():
    """获取会话工厂"""
    engine = create_database_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def init_database():
    """初始化数据库表"""
    engine = create_database_engine()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created successfully")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话"""
    SessionLocal = get_sessionmaker()

    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_database():
    """关闭数据库连接"""
    engine = create_database_engine()
    await engine.dispose()
    logger.info("Database connections closed")
