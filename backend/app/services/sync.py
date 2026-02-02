from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import hashlib
import logging
from pathlib import Path
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    Source,
    Skill,
    SkillAnalysis,
    Conflict,
    MergedSkill,
    RenamingRecord,
    DecisionHistory,
    SyncLog,
)
from ..config import config
from .github import get_github_service
from .analyzer import get_analyzer

logger = logging.getLogger(__name__)


class SyncState:
    """同步状态枚举"""

    IDLE = "IDLE"
    PULLING = "PULLING"
    ANALYZING = "ANALYZING"
    MERGING = "MERGING"
    READY = "READY"
    PARTIAL_READY = "PARTIAL_READY"


class SyncService:
    """同步服务"""

    def __init__(self):
        self.github = get_github_service()
        self.analyzer = get_analyzer()
        self.state = SyncState.IDLE
        self.current_action = ""

    async def trigger_sync(self, session: AsyncSession) -> Dict[str, Any]:
        """触发同步"""
        self.state = SyncState.PULLING
        self.current_action = "正在拉取仓库"

        sync_log = None

        try:
            # 记录同步日志
            sync_log = SyncLog(
                id=str(datetime.utcnow().timestamp()),
                action="sync",
                status="running",
                details={},
            )
            session.add(sync_log)
            await session.commit()

            # 获取订阅源
            sources = await self._get_sources(session)

            # 拉取所有仓库
            all_skills = []
            for source in sources:
                skills = await self._pull_source(session, source)
                all_skills.extend(skills)

            # 分析 Skills
            self.state = SyncState.ANALYZING
            self.current_action = "正在分析 Skills"
            analyzed_skills = await self._analyze_skills(session, all_skills)

            # 检测和处理冲突
            self.state = SyncState.MERGING
            self.current_action = "正在处理冲突"
            await self._detect_and_resolve_conflicts(session, analyzed_skills)

            # 更新状态
            ready_count = await self._get_ready_count(session)
            blocked_count = await self._get_blocked_count(session)

            if blocked_count > 0:
                self.state = SyncState.PARTIAL_READY
            else:
                self.state = SyncState.READY

            # 更新同步日志
            sync_log.status = "success"
            sync_log.details = {
                "ready_count": ready_count,
                "blocked_count": blocked_count,
            }
            await session.commit()

            return {
                "state": self.state,
                "ready_count": ready_count,
                "blocked_count": blocked_count,
                "message": f"同步完成 - {ready_count} 个就绪, {blocked_count} 个待处理",
            }

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self.state = SyncState.IDLE

            if sync_log is not None:
                sync_log.status = "failed"
                sync_log.details = {"error": str(e)}
                await session.commit()

            raise

    async def _get_sources(self, session: AsyncSession) -> List[Source]:
        """获取所有订阅源"""
        result = await session.execute(select(Source))
        return list(result.scalars().all())

    async def _pull_source(
        self, session: AsyncSession, source: Source
    ) -> List[Dict[str, Any]]:
        """拉取单个订阅源"""
        logger.info(f"Pulling source: {source.name}")

        try:
            # 克隆或更新仓库
            repo_name, repo_path = await self.github.clone_repository(
                repo_url=source.url,
                sub_path=source.sub_path,
                access_token=source.access_token,
            )

            # 获取最新 commit hash
            commit_hash = await self.github.get_commit_hash(repo_path)

            # 查找 Skills
            skill_paths = self.github.find_skills(repo_path)

            # 读取 Skills 内容
            skills = []
            for skill_path in skill_paths:
                skill_data = self.github.read_skill_content(skill_path)
                skill_data["repo_name"] = source.name
                skills.append(skill_data)

            # 更新订阅源信息
            source.last_commit = commit_hash
            source.last_sync_at = datetime.utcnow()
            source.skill_count = len(skills)

            await session.commit()

            # 清理临时目录
            if str(repo_path).startswith("/tmp"):
                import shutil

                shutil.rmtree(repo_path, ignore_errors=True)

            return skills

        except Exception as e:
            logger.error(f"Failed to pull source {source.name}: {e}")
            raise

    async def _analyze_skills(
        self,
        session: AsyncSession,
        skills: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """分析 Skills"""
        analyzed_skills = []

        for skill in skills:
            try:
                # 分析 Skill
                analysis = await self.analyzer.analyze_skill(
                    repo_name=skill["repo_name"],
                    skill_name=skill["name"],
                    skill_content=skill["content"],
                    file_list=[s["name"] for s in skill.get("scripts", [])],
                )

                skill["analysis"] = analysis
                analyzed_skills.append(skill)

            except Exception as e:
                logger.warning(f"Failed to analyze skill {skill['name']}: {e}")
                skill["analysis"] = {
                    "summary": "",
                    "quality_score": 0,
                    "quality_issues": [f"分析失败: {e}"],
                }
                analyzed_skills.append(skill)

        return analyzed_skills

    async def _detect_and_resolve_conflicts(
        self,
        session: AsyncSession,
        skills: List[Dict[str, Any]],
    ):
        """检测和处理冲突"""
        # 按名称分组
        skills_by_name: Dict[str, List[Dict[str, Any]]] = {}
        for skill in skills:
            name = skill["name"]
            if name not in skills_by_name:
                skills_by_name[name] = []
            skills_by_name[name].append(skill)

        # 检测同名冲突
        for name, same_name_skills in skills_by_name.items():
            if len(same_name_skills) > 1:
                await self._handle_name_conflict(session, name, same_name_skills)

    async def _handle_name_conflict(
        self,
        session: AsyncSession,
        skill_name: str,
        skills: List[Dict[str, Any]],
    ):
        """处理同名冲突"""
        # 检查是否可以沿用历史决策
        reuse_decision = await self._check_reuse_decision(session, skills)

        if reuse_decision:
            # 沿用历史决策
            await self._apply_decision(
                session, skills, reuse_decision, auto_reused=True
            )
            return

        # 需要用户决策
        conflict = Conflict(
            id=str(datetime.utcnow().timestamp()),
            type="name_conflict",
            skill_ids=[s.get("id", "") for s in skills],
            skill_hashes={s.get("id", ""): s.get("content_hash", "") for s in skills},
            status="pending",
        )
        session.add(conflict)
        await session.commit()

    async def _check_reuse_decision(
        self,
        session: AsyncSession,
        skills: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """检查是否可以沿用历史决策"""
        # 查找最近的相关决策
        result = await session.execute(
            select(DecisionHistory)
            .where(DecisionHistory.skill_ids.contains([skills[0].get("id", "")]))
            .order_by(DecisionHistory.created_at.desc())
            .limit(1)
        )
        decision = result.scalar_one_or_none()

        if not decision:
            return None

        # 检查 hash 是否变化
        old_hashes = decision.skill_hashes or {}
        new_hashes = {s.get("id", ""): s.get("content_hash", "") for s in skills}

        # 统计变化
        changed = sum(1 for k in new_hashes if old_hashes.get(k) != new_hashes[k])
        unchanged = sum(1 for k in new_hashes if old_hashes.get(k) == new_hashes[k])

        # 如果只有一方变化，沿用决策
        if changed <= 1:
            return decision.decision

        # 如果双方都变化，需要 AI 重新评估
        # 这里简化处理，返回 None 让用户重新决策
        return None

    async def _apply_decision(
        self,
        session: AsyncSession,
        skills: List[Dict[str, Any]],
        decision: Dict[str, Any],
        auto_reused: bool = False,
    ):
        """应用决策"""
        # 创建 Skill 记录
        chosen_skill = skills[0]  # 简化处理

        skill = Skill(
            id=str(datetime.utcnow().timestamp()),
            name=chosen_skill["name"],
            source_id=chosen_skill.get("source_id", ""),
            path=chosen_skill.get("path", ""),
            content_hash=chosen_skill.get("content_hash", ""),
            status="ready",
        )
        session.add(skill)

        # 创建分析记录
        if chosen_skill.get("analysis"):
            analysis = SkillAnalysis(
                id=str(datetime.utcnow().timestamp()),
                skill_id=skill.id,
                summary=chosen_skill["analysis"].get("summary", ""),
                description=chosen_skill["analysis"].get("description", ""),
                use_cases=chosen_skill["analysis"].get("use_cases", []),
                triggers=chosen_skill["analysis"].get("triggers", []),
                dependencies=chosen_skill["analysis"].get("dependencies", {}),
                quality_score=chosen_skill["analysis"].get("quality_score", 0),
                quality_issues=chosen_skill["analysis"].get("quality_issues", []),
                tags=chosen_skill["analysis"].get("tags", []),
            )
            session.add(analysis)

        # 记录决策历史
        decision_history = DecisionHistory(
            id=str(datetime.utcnow().timestamp()),
            conflict_type="name_conflict",
            skill_ids=[s.get("id", "") for s in skills],
            skill_hashes={s.get("id", ""): s.get("content_hash", "") for s in skills},
            decision=decision,
            reasoning="自动沿用历史决策" if auto_reused else "用户手动决策",
        )
        session.add(decision_history)

        await session.commit()

    async def _get_ready_count(self, session: AsyncSession) -> int:
        """获取就绪的 Skills 数量"""
        result = await session.execute(select(Skill).where(Skill.status == "ready"))
        return len(result.scalars().all())

    async def _get_blocked_count(self, session: AsyncSession) -> int:
        """获取阻塞的 Skills 数量"""
        result = await session.execute(select(Skill).where(Skill.status == "blocked"))
        return len(result.scalars().all())

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "state": self.state,
            "current_action": self.current_action,
        }


# 创建全局实例
_sync_service: Optional[SyncService] = None


def get_sync_service() -> SyncService:
    """获取 Sync Service 实例"""
    global _sync_service
    if _sync_service is None:
        _sync_service = SyncService()
    return _sync_service
