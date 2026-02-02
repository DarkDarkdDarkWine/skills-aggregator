import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import get_db
from app.models import Base, Source, Skill, Conflict, SkillAnalysis


# ============ Fixture: 异步事件循环 ============


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环 fixture"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============ Fixture: 测试数据库引擎 ============


@pytest.fixture
def test_engine():
    """创建测试数据库引擎（使用内存 SQLite）"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=NullPool,
        echo=False,
    )
    return engine


@pytest.fixture
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _sessionmaker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with _sessionmaker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def client(test_db: AsyncSession) -> Generator[TestClient, None, None]:
    """创建测试客户端"""

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建异步测试客户端"""

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ============ Fixture: Mock 数据 ============


@pytest.fixture
def sample_source() -> Source:
    """创建测试用订阅源"""
    return Source(
        id=str(uuid.uuid4()),
        name="test-repo",
        url="https://github.com/test/repo",
        priority=1,
        sub_path="skills",
        access_token=None,
        skill_count=0,
    )


@pytest.fixture
def sample_skill() -> Skill:
    """创建测试用 Skill"""
    return Skill(
        id=str(uuid.uuid4()),
        name="test-skill",
        source_id=str(uuid.uuid4()),
        path="skills/test-skill",
        content_hash="abc123",
        status="ready",
    )


@pytest.fixture
def sample_conflict() -> Conflict:
    """创建测试用冲突"""
    skill_id = str(uuid.uuid4())
    return Conflict(
        id=str(uuid.uuid4()),
        type="name_conflict",
        skill_ids=[skill_id],
        skill_hashes={skill_id: "abc123"},
        status="pending",
    )


@pytest.fixture
def sample_skill_analysis() -> SkillAnalysis:
    """创建测试用分析结果"""
    return SkillAnalysis(
        id=str(uuid.uuid4()),
        skill_id=str(uuid.uuid4()),
        summary="测试技能摘要",
        description="这是一个测试技能",
        use_cases=["测试场景1", "测试场景2"],
        triggers=["test", "测试"],
        dependencies={"scripts": []},
        quality_score=85,
        quality_issues=[],
        tags=["test", "example"],
    )


# ============ Fixture: Mock 服务 ============


@pytest.fixture
def mock_ai_provider():
    """Mock AI Provider"""
    with patch("app.services.ai_provider.get_ai_provider") as mock:
        provider = AsyncMock()
        provider.analyze = AsyncMock(
            return_value={
                "summary": "测试摘要",
                "quality_score": 85,
                "tags": ["test"],
            }
        )
        provider.chat = AsyncMock(return_value='{"result": "test"}')
        mock.return_value = provider
        yield mock


@pytest.fixture
def mock_github_service():
    """Mock GitHub 服务"""
    with patch("app.services.github.get_github_service") as mock:
        service = MagicMock()
        service.clone_repository = AsyncMock(
            return_value=(
                "test-repo",
                "/tmp/test-repo",
            )
        )
        service.get_commit_hash = AsyncMock(return_value="abc123def")
        service.find_skills = MagicMock(return_value=[])
        service.read_skill_content = MagicMock(
            return_value={
                "name": "test-skill",
                "content": "# Test Skill\n\nTest content",
                "content_hash": "abc123",
                "scripts": [],
            }
        )
        mock.return_value = service
        yield mock


@pytest.fixture
def mock_sync_service():
    """Mock Sync 服务"""
    with patch("app.services.sync.get_sync_service") as mock:
        service = MagicMock()
        service.trigger_sync = AsyncMock(
            return_value={
                "state": "READY",
                "ready_count": 10,
                "blocked_count": 0,
                "message": "同步完成",
            }
        )
        service.get_status = MagicMock(
            return_value={
                "state": "IDLE",
                "current_action": "",
            }
        )
        mock.return_value = service
        yield mock


# ============ Helper 函数 ============


def generate_test_skill_md(name: str = "test-skill") -> str:
    """生成测试用的 SKILL.md 内容"""
    return f"""---
name: {name}
description: 这是一个测试技能
---

# {name}

这是一个测试技能的详细描述。

## 使用场景

- 测试场景1
- 测试场景2

## 触发关键词

- test
- 测试
"""


def create_test_source_dict(**overrides) -> dict:
    """创建测试用订阅源字典"""
    defaults = {
        "name": "test-source",
        "url": "https://github.com/test/repo",
        "priority": 1,
        "sub_path": "skills",
        "access_token": None,
    }
    defaults.update(overrides)
    return defaults
