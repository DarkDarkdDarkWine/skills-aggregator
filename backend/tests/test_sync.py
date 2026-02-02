"""测试同步服务"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.sync import SyncService, SyncState, get_sync_service


class TestSyncService:
    """测试同步服务"""

    @pytest.fixture
    def sync_service(self):
        """创建同步服务实例"""
        return SyncService()

    def test_initial_state(self, sync_service):
        """测试初始状态"""
        assert sync_service.state == SyncState.IDLE
        assert sync_service.current_action == ""

    def test_get_status_idle(self, sync_service):
        """测试获取空闲状态"""
        status = sync_service.get_status()

        assert status["state"] == SyncState.IDLE
        assert status["current_action"] == ""

    @pytest.mark.asyncio
    async def test_trigger_sync_no_sources(self, sync_service, test_db):
        """测试无订阅源时的同步"""
        with patch.object(
            sync_service, "_get_sources", new_callable=AsyncMock
        ) as mock_sources:
            mock_sources.return_value = []

            result = await sync_service.trigger_sync(test_db)

            assert result["state"] == SyncState.READY
            assert result["ready_count"] == 0
            assert result["blocked_count"] == 0

    @pytest.mark.asyncio
    async def test_trigger_sync_with_sources(
        self, sync_service, test_db, sample_source
    ):
        """测试有订阅源时的同步"""
        # Mock GitHub 服务
        mock_github = MagicMock()
        mock_github.clone_repository = AsyncMock(
            return_value=(
                "test-repo",
                "/tmp/test-repo",
            )
        )
        mock_github.get_commit_hash = AsyncMock(return_value="abc123")
        mock_github.find_skills = MagicMock(return_value=[])
        mock_github.read_skill_content = MagicMock(
            return_value={
                "name": "test-skill",
                "content": "# Test",
                "content_hash": "hash123",
                "scripts": [],
                "repo_name": "test-repo",
            }
        )

        # Mock AI 分析器
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_skill = AsyncMock(
            return_value={
                "summary": "测试",
                "quality_score": 85,
                "tags": ["test"],
            }
        )
        mock_analyzer.compare_skills = AsyncMock(return_value={})
        mock_analyzer.cluster_skills = AsyncMock(return_value={})

        with patch("app.services.sync.get_github_service", return_value=mock_github):
            with patch("app.services.sync.get_analyzer", return_value=mock_analyzer):
                with patch.object(
                    sync_service, "_get_sources", new_callable=AsyncMock
                ) as mock_sources:
                    mock_sources.return_value = [sample_source]

                    result = await sync_service.trigger_sync(test_db)

                    assert result["state"] == SyncState.READY


class TestSyncState:
    """测试同步状态"""

    def test_state_values(self):
        """测试状态值"""
        assert SyncState.IDLE == "IDLE"
        assert SyncState.PULLING == "PULLING"
        assert SyncState.ANALYZING == "ANALYZING"
        assert SyncState.MERGING == "MERGING"
        assert SyncState.READY == "READY"
        assert SyncState.PARTIAL_READY == "PARTIAL_READY"

    def test_state_transition(self):
        """测试状态转换"""
        service = SyncService()

        # 初始状态
        assert service.state == SyncState.IDLE

        # 开始拉取
        service.state = SyncState.PULLING
        assert service.state == SyncState.PULLING

        # 开始分析
        service.state = SyncState.ANALYZING
        assert service.state == SyncState.ANALYZING

        # 合并中
        service.state = SyncState.MERGING
        assert service.state == SyncState.MERGING

        # 完成（有冲突）
        service.state = SyncState.PARTIAL_READY
        assert service.state == SyncState.PARTIAL_READY

        # 完成（无冲突）
        service.state = SyncState.READY
        assert service.state == SyncState.READY


class TestConflictResolution:
    """测试冲突解决逻辑"""

    @pytest.fixture
    def sync_service(self):
        """创建同步服务实例"""
        return SyncService()

    @pytest.mark.asyncio
    async def test_check_reuse_decision_no_history(self, sync_service, test_db):
        """测试无历史决策时"""
        result = await sync_service._check_reuse_decision(
            test_db, [{"id": "skill1", "content_hash": "hash1"}]
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_check_reuse_decision_unchanged(self, sync_service, test_db):
        """测试 skill 未变化时沿用决策"""
        from app.models import DecisionHistory

        # 添加历史决策
        decision = DecisionHistory(
            id="decision-1",
            conflict_type="name_conflict",
            skill_ids=["skill1"],
            skill_hashes={"skill1": "hash1"},
            decision={"action": "choose_one", "chosen": "skill1"},
        )
        test_db.add(decision)
        await test_db.commit()

        # 检查是否可以沿用
        result = await sync_service._check_reuse_decision(
            test_db, [{"id": "skill1", "content_hash": "hash1"}]
        )

        assert result is not None
        assert result["action"] == "choose_one"


class TestGetSyncService:
    """测试获取同步服务实例"""

    def teardown_method(self):
        """清理全局实例"""
        import app.services.sync

        app.services.sync._sync_service = None

    def test_get_service_singleton(self, tmp_path):
        """测试服务是单例"""
        with patch("app.services.sync.get_github_service") as mock_github:
            with patch("app.services.sync.get_analyzer") as mock_analyzer:
                mock_github.return_value = MagicMock()
                mock_analyzer.return_value = MagicMock()

                service1 = get_sync_service()
                service2 = get_sync_service()

                assert service1 is service2
