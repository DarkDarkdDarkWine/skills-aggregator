"""测试 AI 分析引擎"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.services.analyzer import AIAnalyzer, get_analyzer


class TestAIAnalyzer:
    """测试 AI 分析引擎"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return AIAnalyzer()

    @pytest.mark.asyncio
    async def test_analyze_skill_success(self, analyzer):
        """测试成功分析 Skill"""
        mock_provider = AsyncMock()
        mock_provider.analyze = AsyncMock(
            return_value={
                "name": "test-skill",
                "summary": "测试摘要",
                "description": "详细描述",
                "use_cases": ["场景1", "场景2"],
                "triggers": ["test"],
                "dependencies": {"scripts": []},
                "quality_score": 85,
                "quality_issues": [],
                "tags": ["test"],
            }
        )

        with patch.object(analyzer, "ai", mock_provider):
            result = await analyzer.analyze_skill(
                repo_name="test-repo",
                skill_name="test-skill",
                skill_content="# Test Skill\n\nTest content",
                file_list=["helper.py"],
            )

        assert result["name"] == "test-skill"
        assert result["summary"] == "测试摘要"
        assert result["quality_score"] == 85

    @pytest.mark.asyncio
    async def test_analyze_skill_with_cache(self, analyzer, tmp_path):
        """测试使用缓存的分析"""
        # 计算正确的缓存 key（根据 skill 内容 hash）
        content = "test content"
        import hashlib

        cache_key = hashlib.md5(
            f"test-repo:cached-skill:{content}".encode()
        ).hexdigest()

        # 创建一个模拟的缓存文件
        cache_content = {
            "name": "cached-skill",
            "summary": "缓存摘要",
            "description": "缓存描述",
            "use_cases": [],
            "triggers": [],
            "dependencies": {},
            "quality_score": 90,
            "quality_issues": [],
            "tags": [],
        }
        cache_file = analyzer.analysis_cache_dir / f"{cache_key}.json"
        cache_file.write_text(
            '{"name": "cached-skill", "summary": "缓存摘要", "description": "缓存描述", "use_cases": [], "triggers": [], "dependencies": {}, "quality_score": 90, "quality_issues": [], "tags": []}'
        )

        # 调用分析器，传入相同内容，应该命中缓存
        result = await analyzer.analyze_skill(
            repo_name="test-repo",
            skill_name="cached-skill",
            skill_content=content,
            file_list=[],
        )

        # 验证结果来自缓存
        assert result["summary"] == "缓存摘要"
        assert result["quality_score"] == 90

    @pytest.mark.asyncio
    async def test_compare_skills(self, analyzer):
        """测试对比 Skills"""
        mock_provider = AsyncMock()
        mock_provider.analyze = AsyncMock(
            return_value={
                "skill_name": "git-commit",
                "comparison": [
                    {
                        "repo": "repo-a",
                        "strengths": ["完整"],
                        "weaknesses": ["无"],
                        "completeness": 95,
                        "quality": 90,
                    }
                ],
                "recommendation": {
                    "action": "choose_one",
                    "chosen": "repo-a",
                    "reason": "更完整",
                },
            }
        )

        skills = [
            {
                "repo_name": "repo-a",
                "priority": 1,
                "content": "# Git Commit\n\nA git commit skill",
                "scripts": [{"name": "commit.py"}],
            },
            {
                "repo_name": "repo-b",
                "priority": 2,
                "content": "# Git Commit\n\nAnother git commit skill",
                "scripts": [{"name": "git.sh"}],
            },
        ]

        with patch.object(analyzer, "ai", mock_provider):
            result = await analyzer.compare_skills(skills)

        assert result["skill_name"] == "git-commit"
        assert result["recommendation"]["action"] == "choose_one"

    @pytest.mark.asyncio
    async def test_cluster_skills(self, analyzer):
        """测试聚类 Skills"""
        mock_provider = AsyncMock()
        mock_provider.analyze = AsyncMock(
            return_value={
                "similar_groups": [
                    {
                        "group_name": "git-related",
                        "description": "Git 相关技能",
                        "skills": [
                            {"name": "git-commit", "repo": "repo-a"},
                            {"name": "git-pr", "repo": "repo-b"},
                        ],
                        "similarity_reason": "都与 git 操作相关",
                        "recommendation": {
                            "action": "keep_all",
                            "reason": "功能不同但互补",
                        },
                    }
                ],
                "unique_skills": [{"name": "test-skill", "repo": "repo-c"}],
            }
        )

        skills = [
            {
                "name": "git-commit",
                "repo_name": "repo-a",
                "summary": "生成 git commit message",
                "tags": ["git"],
                "triggers": ["commit", "git"],
            },
            {
                "name": "git-pr",
                "repo_name": "repo-b",
                "summary": "创建 pull request",
                "tags": ["git", "github"],
                "triggers": ["pr", "github"],
            },
            {
                "name": "test-skill",
                "repo_name": "repo-c",
                "summary": "测试技能",
                "tags": ["test"],
                "triggers": ["test"],
            },
        ]

        with patch.object(analyzer, "ai", mock_provider):
            result = await analyzer.cluster_skills(skills)

        assert "similar_groups" in result
        assert len(result["similar_groups"]) == 1

    @pytest.mark.asyncio
    async def test_merge_skills(self, analyzer):
        """测试合并 Skills"""
        mock_provider = AsyncMock()
        mock_provider.analyze = AsyncMock(
            return_value={
                "merged_skill": {
                    "name": "git-super",
                    "skill_md": "# Git Super\n\nCombined git skill",
                    "scripts": [{"filename": "git_helper.py", "content": "# Combined"}],
                    "renaming_records": [],
                    "kept_from": {
                        "repo-a": ["commit 功能"],
                        "repo-b": ["pr 功能"],
                    },
                    "improvements": ["整合了多个 git 功能"],
                }
            }
        )

        skills = [
            {
                "repo_name": "repo-a",
                "name": "git-commit",
                "content": "# Git Commit\n\nCommit functionality",
                "scripts": [{"name": "commit.py", "content": "# commit"}],
            },
            {
                "repo_name": "repo-b",
                "name": "git-pr",
                "content": "# Git PR\n\nPR functionality",
                "scripts": [{"name": "pr.py", "content": "# pr"}],
            },
        ]

        with patch.object(analyzer, "ai", mock_provider):
            result = await analyzer.merge_skills(skills)

        assert result["merged_skill"]["name"] == "git-super"
        assert "kept_from" in result["merged_skill"]

    @pytest.mark.asyncio
    async def test_merge_skills_with_history(self, analyzer):
        """测试带历史记录的合并"""
        mock_provider = AsyncMock()
        mock_provider.analyze = AsyncMock(
            return_value={
                "merged_skill": {
                    "name": "git-merged",
                    "skill_md": "# Git Merged\n\nCombined skill",
                    "scripts": [{"filename": "git_helper.py", "content": "# helper"}],
                    "renaming_records": [
                        {
                            "original_filename": "helper.py",
                            "assigned_filename": "a_helper.py",
                            "source_repo": "repo-a",
                            "reasoning": "添加前缀避免冲突",
                        }
                    ],
                    "kept_from": {"repo-a": ["commit 功能"]},
                    "improvements": ["整合了多个功能"],
                }
            }
        )

        skills = [
            {
                "repo_name": "repo-a",
                "name": "skill-a",
                "content": "# Skill A",
                "scripts": [{"name": "helper.py", "content": "# helper"}],
            },
        ]

        renaming_history = [
            {
                "original_filename": "helper.py",
                "assigned_filename": "a_helper.py",
                "source_repo": "repo-a",
                "reasoning": "添加前缀避免冲突",
            }
        ]

        with patch.object(analyzer, "ai", mock_provider):
            result = await analyzer.merge_skills(
                skills, renaming_history=renaming_history
            )

        assert "merged_skill" in result
        assert result["merged_skill"]["name"] == "git-merged"


class TestAnalyzerPromptFormats:
    """测试分析器提示词格式"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return AIAnalyzer()

    def test_analysis_format(self, analyzer):
        """测试分析结果格式"""
        format_str = analyzer._get_analysis_format()
        assert '"name":' in format_str
        assert '"summary":' in format_str
        assert '"quality_score":' in format_str

    def test_comparison_format(self, analyzer):
        """测试对比结果格式"""
        format_str = analyzer._get_comparison_format()
        assert '"comparison":' in format_str
        assert '"recommendation":' in format_str

    def test_cluster_format(self, analyzer):
        """测试聚类结果格式"""
        format_str = analyzer._get_cluster_format()
        assert '"similar_groups":' in format_str
        assert '"unique_skills":' in format_str

    def test_merge_format(self, analyzer):
        """测试合并结果格式"""
        format_str = analyzer._get_merge_format()
        assert '"merged_skill":' in format_str
        assert '"renaming_records":' in format_str
