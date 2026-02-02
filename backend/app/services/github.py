import os
import shutil
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging

import asyncio
from git import Repo, GitCommandError

from ..config import config

logger = logging.getLogger(__name__)


class GitHubService:
    """GitHub 服务"""

    def __init__(self, sources_dir: Optional[str] = None):
        self.sources_dir = Path(sources_dir or config.storage.sources_dir)
        self.sources_dir.mkdir(parents=True, exist_ok=True)

    async def clone_repository(
        self,
        repo_url: str,
        sub_path: str = "",
        access_token: Optional[str] = None,
        depth: int = 1,
    ) -> Tuple[str, Path]:
        """
        克隆 GitHub 仓库

        Returns:
            repo_name: 仓库名称
            repo_path: 仓库本地路径
        """
        # 解析仓库信息
        if repo_url.endswith("/"):
            repo_url = repo_url[:-1]

        # 添加 token 认证（如果是私有仓库）
        if access_token and "github.com" in repo_url:
            if repo_url.startswith("https://"):
                repo_url = repo_url.replace("https://", f"https://{access_token}@")

        # 生成临时目录
        temp_dir = Path(tempfile.mkdtemp(prefix="skills_"))

        try:
            # 克隆仓库
            logger.info(f"Cloning repository: {repo_url}")

            if depth > 0:
                await asyncio.to_thread(
                    Repo.clone_from,
                    repo_url,
                    temp_dir,
                    depth=depth,
                    multi_options=["--no-single-branch"] if depth > 1 else [],
                )
            else:
                await asyncio.to_thread(
                    Repo.clone_from,
                    repo_url,
                    temp_dir,
                )

            # 获取仓库名称
            repo_name = temp_dir.name

            # 如果指定了 sub_path，移动内容
            if sub_path:
                target_path = self.sources_dir / repo_name
                sub_path_obj = temp_dir / sub_path

                if sub_path_obj.exists():
                    if target_path.exists():
                        shutil.rmtree(target_path)
                    shutil.copytree(sub_path_obj, target_path)
                    shutil.rmtree(temp_dir)
                    return repo_name, target_path
                else:
                    logger.warning(f"Sub path {sub_path} not found in repository")
                    shutil.rmtree(temp_dir)
                    raise ValueError(f"Sub path {sub_path} not found in repository")

            return repo_name, temp_dir

        except GitCommandError as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.error(f"Failed to clone repository: {e}")
            raise

    async def get_commit_hash(self, repo_path: Path) -> str:
        """获取仓库的最新 commit hash"""
        try:
            repo = Repo(repo_path)
            return repo.head.commit.hexsha
        except Exception as e:
            logger.error(f"Failed to get commit hash: {e}")
            return ""

    async def pull_repository(self, repo_path: Path) -> bool:
        """更新仓库"""
        try:
            repo = Repo(repo_path)
            origin = repo.remotes.origin
            origin.pull()
            return True
        except Exception as e:
            logger.error(f"Failed to pull repository: {e}")
            return False

    def find_skills(self, repo_path: Path) -> List[Path]:
        """查找目录下的所有 Skills"""
        skills = []

        for root, dirs, files in os.walk(repo_path):
            # 跳过隐藏目录和特定目录
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in ["__pycache__", "node_modules"]
            ]

            # 查找 SKILL.md 文件
            if "SKILL.md" in files:
                skill_path = Path(root)
                skills.append(skill_path)

        return skills

    def read_skill_content(self, skill_path: Path) -> Dict[str, Any]:
        """读取 Skill 内容"""
        skill_md_path = skill_path / "SKILL.md"

        if not skill_md_path.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_path}")

        content = skill_md_path.read_text(encoding="utf-8")

        # 计算 content hash
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

        # 收集附带文件
        scripts = []
        for file_path in skill_path.iterdir():
            if file_path.name == "SKILL.md":
                continue
            if file_path.is_file():
                scripts.append(
                    {
                        "name": file_path.name,
                        "path": str(file_path.relative_to(skill_path)),
                    }
                )

        return {
            "name": skill_path.name,
            "path": str(skill_path),
            "content": content,
            "content_hash": content_hash,
            "scripts": scripts,
        }

    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件内容 hash"""
        if not file_path.exists():
            return ""

        content = file_path.read_bytes()
        return hashlib.md5(content).hexdigest()


# 创建全局实例
_github_service: Optional[GitHubService] = None


def get_github_service() -> GitHubService:
    """获取 GitHub Service 实例"""
    global _github_service
    if _github_service is None:
        _github_service = GitHubService()
    return _github_service
