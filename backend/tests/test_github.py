"""测试 GitHub 服务"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import os

from app.services.github import GitHubService, get_github_service


class TestGitHubService:
    """测试 GitHub 服务"""

    @pytest.fixture
    def github_service(self, tmp_path):
        """创建 GitHub 服务实例"""
        service = GitHubService(sources_dir=str(tmp_path))
        return service

    def test_initialization(self, github_service):
        """测试初始化"""
        assert github_service.sources_dir.exists()

    def test_find_skills(self, github_service, tmp_path):
        """测试查找 Skills"""
        # 创建测试目录结构
        skill_dir = tmp_path / "test-repo" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        another_dir = tmp_path / "test-repo" / "skills" / "another-skill"
        another_dir.mkdir(parents=True)
        (another_dir / "SKILL.md").write_text("# Another Skill")

        # 查找 Skills
        skills = github_service.find_skills(tmp_path / "test-repo")

        assert len(skills) == 2
        skill_names = [s.name for s in skills]
        assert "test-skill" in skill_names
        assert "another-skill" in skill_names

    def test_find_skills_excludes_hidden(self, github_service, tmp_path):
        """测试查找 Skills 排除隐藏目录"""
        skill_dir = tmp_path / "test-repo" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test")

        hidden_dir = tmp_path / "test-repo" / "skills" / ".hidden-skill"
        hidden_dir.mkdir(parents=True)
        (hidden_dir / "SKILL.md").write_text("# Hidden")

        skills = github_service.find_skills(tmp_path / "test-repo")

        assert len(skills) == 1
        assert skills[0].name == "test-skill"

    def test_read_skill_content(self, github_service, tmp_path):
        """测试读取 Skill 内容"""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill\n\nContent")

        result = github_service.read_skill_content(skill_dir)

        assert result["name"] == "test-skill"
        assert "Test Skill" in result["content"]
        assert "content_hash" in result
        assert len(result["scripts"]) == 0

    def test_read_skill_content_with_scripts(self, github_service, tmp_path):
        """测试读取带脚本的 Skill"""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test")
        (skill_dir / "helper.py").write_text("# Helper")
        (skill_dir / "utils.sh").write_text("# Utils")

        result = github_service.read_skill_content(skill_dir)

        assert len(result["scripts"]) == 2
        script_names = [s["name"] for s in result["scripts"]]
        assert "helper.py" in script_names
        assert "utils.sh" in script_names

    def test_read_skill_content_not_found(self, github_service, tmp_path):
        """测试读取不存在的 Skill"""
        skill_dir = tmp_path / "non-existent"
        skill_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="SKILL.md not found"):
            github_service.read_skill_content(skill_dir)

    def test_calculate_file_hash(self, github_service, tmp_path):
        """测试计算文件 hash"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        hash1 = github_service.calculate_file_hash(test_file)
        hash2 = github_service.calculate_file_hash(test_file)

        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length

    def test_calculate_file_hash_nonexistent(self, github_service, tmp_path):
        """测试计算不存在的文件 hash"""
        nonexistent = tmp_path / "nonexistent.txt"

        hash_value = github_service.calculate_file_hash(nonexistent)

        assert hash_value == ""


class TestGitHubServiceAsync:
    """测试 GitHub 服务异步方法"""

    @pytest.mark.asyncio
    async def test_get_commit_hash(self, tmp_path):
        """测试获取 commit hash"""
        # 创建临时 git 仓库
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        import subprocess

        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        (repo_dir / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=repo_dir, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"], cwd=repo_dir, capture_output=True
        )

        service = GitHubService(sources_dir=str(tmp_path))
        commit_hash = await service.get_commit_hash(repo_dir)

        assert len(commit_hash) == 40  # Git commit hash length


class TestGetGitHubService:
    """测试获取 GitHub 服务实例"""

    def teardown_method(self):
        """清理全局实例"""
        import app.services.github

        app.services.github._github_service = None

    def test_get_service_singleton(self, tmp_path):
        """测试服务是单例"""
        with patch("app.services.github.config") as mock_config:
            mock_storage = MagicMock()
            mock_storage.sources_dir = str(tmp_path)
            mock_config.storage = mock_storage

            service1 = get_github_service()
            service2 = get_github_service()

            assert service1 is service2
