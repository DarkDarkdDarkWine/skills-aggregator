from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel, Field

from ..database import get_db
from ..models import Source, Skill, Conflict, SkillAnalysis
from ..services.sync import get_sync_service
from ..services.github import get_github_service
from ..logger import log_buffer, log_buffer_lock

router = APIRouter(prefix="/api", tags=["API"])


# ============ 请求/响应模型 ============


class SourceCreate(BaseModel):
    """创建订阅源"""

    name: str = Field(..., description="订阅源名称")
    url: str = Field(..., description="GitHub 仓库 URL")
    priority: int = Field(default=0, description="优先级")
    sub_path: str = Field(default="", description="Skills 子目录")
    access_token: Optional[str] = Field(default=None, description="私有仓库访问令牌")


class SourceUpdate(BaseModel):
    """更新订阅源"""

    name: Optional[str] = None
    priority: Optional[int] = None
    sub_path: Optional[str] = None
    access_token: Optional[str] = None


class SyncResponse(BaseModel):
    """同步响应"""

    state: str
    ready_count: int
    blocked_count: int
    message: str


class ConflictResolve(BaseModel):
    """冲突解决"""

    action: str = Field(..., description="处理方式: choose_one, keep_all, merge")
    chosen_skill_id: Optional[str] = Field(default=None, description="选择的 Skill ID")
    merged_content: Optional[str] = Field(default=None, description="合并后的内容")


# ============ 订阅源 API ============


@router.post("/sources")
async def create_source(source: SourceCreate, db: AsyncSession = Depends(get_db)):
    """添加订阅源"""
    import uuid

    new_source = Source(
        id=str(uuid.uuid4()),
        name=source.name,
        url=source.url,
        priority=source.priority,
        sub_path=source.sub_path,
        access_token=source.access_token,
    )
    db.add(new_source)
    await db.commit()
    await db.refresh(new_source)
    return new_source


@router.get("/sources")
async def list_sources(db: AsyncSession = Depends(get_db)):
    """获取订阅源列表"""
    result = await db.execute(select(Source))
    sources = result.scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "url": s.url,
            "priority": s.priority,
            "sub_path": s.sub_path,
            "skill_count": s.skill_count,
            "last_sync_at": s.last_sync_at.isoformat() if s.last_sync_at else None,
        }
        for s in sources
    ]


@router.put("/sources/{source_id}")
async def update_source(
    source_id: str,
    update_data: SourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新订阅源"""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="订阅源不存在")

    if update_data.name is not None:
        source.name = update_data.name
    if update_data.priority is not None:
        source.priority = update_data.priority
    if update_data.sub_path is not None:
        source.sub_path = update_data.sub_path
    if update_data.access_token is not None:
        source.access_token = update_data.access_token

    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/sources/{source_id}")
async def delete_source(source_id: str, db: AsyncSession = Depends(get_db)):
    """删除订阅源"""
    await db.execute(delete(Source).where(Source.id == source_id))
    await db.commit()
    return {"message": "删除成功"}


# ============ 同步 API ============


@router.post("/sync")
async def trigger_sync(db: AsyncSession = Depends(get_db)):
    """触发同步"""
    sync_service = get_sync_service()
    return await sync_service.trigger_sync(db)


@router.get("/sync/status")
async def get_sync_status(db: AsyncSession = Depends(get_db)):
    """获取同步状态"""
    sync_service = get_sync_service()
    status = sync_service.get_status()

    # 获取 Skills 统计
    ready_result = await db.execute(select(Skill).where(Skill.status == "ready"))
    blocked_result = await db.execute(select(Skill).where(Skill.status == "blocked"))

    ready_count = len(ready_result.scalars().all())
    blocked_count = len(blocked_result.scalars().all())

    # 获取冲突列表
    conflicts_result = await db.execute(
        select(Conflict).where(Conflict.status == "pending")
    )
    conflicts = [
        {
            "id": c.id,
            "type": c.type,
            "skill_ids": c.skill_ids,
            "ai_recommendation": c.ai_recommendation,
        }
        for c in conflicts_result.scalars().all()
    ]

    return {
        **status,
        "ready_count": ready_count,
        "blocked_count": blocked_count,
        "conflicts": conflicts,
    }


# ============ Skills API ============


@router.get("/skills")
async def list_skills(
    status: Optional[str] = Query(None, description="状态筛选: ready, blocked"),
    db: AsyncSession = Depends(get_db),
):
    """获取 Skills 列表"""
    query = select(Skill)
    if status:
        query = query.where(Skill.status == status)

    result = await db.execute(query)
    skills = result.scalars().all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "source_id": s.source_id,
            "path": s.path,
            "status": s.status,
            "content_hash": s.content_hash,
        }
        for s in skills
    ]


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str, db: AsyncSession = Depends(get_db)):
    """获取 Skill 详情"""
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill 不存在")

    # 获取分析结果
    analysis_result = await db.execute(
        select(SkillAnalysis).where(SkillAnalysis.skill_id == skill_id)
    )
    analysis = analysis_result.scalar_one_or_none()

    return {
        "id": skill.id,
        "name": skill.name,
        "source_id": skill.source_id,
        "path": skill.path,
        "content_hash": skill.content_hash,
        "status": skill.status,
        "analysis": {
            "summary": analysis.summary if analysis else None,
            "description": analysis.description if analysis else None,
            "quality_score": analysis.quality_score if analysis else None,
            "tags": analysis.tags if analysis else [],
        }
        if analysis
        else None,
    }


# ============ 冲突 API ============


@router.get("/conflicts")
async def list_conflicts(db: AsyncSession = Depends(get_db)):
    """获取冲突列表"""
    result = await db.execute(select(Conflict).where(Conflict.status == "pending"))
    conflicts = result.scalars().all()

    return [
        {
            "id": c.id,
            "type": c.type,
            "skill_ids": c.skill_ids,
            "skill_hashes": c.skill_hashes,
            "ai_recommendation": c.ai_recommendation,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in conflicts
    ]


@router.get("/conflicts/{conflict_id}")
async def get_conflict(conflict_id: str, db: AsyncSession = Depends(get_db)):
    """获取冲突详情"""
    result = await db.execute(select(Conflict).where(Conflict.id == conflict_id))
    conflict = result.scalar_one_or_none()

    if not conflict:
        raise HTTPException(status_code=404, detail="冲突不存在")

    # 获取相关的 Skills
    skills_result = await db.execute(
        select(Skill).where(Skill.id.in_(conflict.skill_ids))
    )
    skills = skills_result.scalars().all()

    return {
        "id": conflict.id,
        "type": conflict.type,
        "skill_ids": conflict.skill_ids,
        "ai_recommendation": conflict.ai_recommendation,
        "skills": [
            {
                "id": s.id,
                "name": s.name,
                "source_id": s.source_id,
                "path": s.path,
            }
            for s in skills
        ],
    }


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    resolution: ConflictResolve,
    db: AsyncSession = Depends(get_db),
):
    """解决冲突"""
    result = await db.execute(select(Conflict).where(Conflict.id == conflict_id))
    conflict = result.scalar_one_or_none()

    if not conflict:
        raise HTTPException(status_code=404, detail="冲突不存在")

    # 更新冲突状态
    conflict.status = "resolved"
    conflict.resolution = resolution.dict()
    conflict.resolved_at = __import__("datetime").datetime.utcnow()

    await db.commit()

    return {"message": "冲突已解决"}


# ============ 下载 API ============


@router.get("/download")
async def download_skills(
    scope: str = Query("ready", description="下载范围: ready, all"),
):
    """下载 Skills"""
    # 这里应该返回实际的 Skills 文件
    # 简化实现，返回元数据
    return {
        "message": "Download endpoint - implement file serving",
        "scope": scope,
    }


@router.get("/metadata")
async def get_metadata(db: AsyncSession = Depends(get_db)):
    """获取元数据"""
    ready_result = await db.execute(select(Skill).where(Skill.status == "ready"))
    blocked_result = await db.execute(select(Skill).where(Skill.status == "blocked"))

    ready_count = len(ready_result.scalars().all())
    blocked_count = len(blocked_result.scalars().all())

    state = "READY" if blocked_count == 0 else "PARTIAL_READY"

    return {
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
        "state": state,
        "ready_count": ready_count,
        "blocked_count": blocked_count,
    }


# ============ 日志 API ============


class LogEntry(BaseModel):
    timestamp: str
    level: str
    logger: str
    message: str
    exc_info: Optional[str] = None


@router.get("/logs", response_model=List[LogEntry])
async def get_logs(limit: int = Query(100, ge=1, le=1000)):
    """获取错误日志"""
    with log_buffer_lock:
        logs = list(log_buffer)[-limit:]
        return logs[::-1]  # 按时间倒序


@router.delete("/logs")
async def clear_logs():
    """清空日志"""
    with log_buffer_lock:
        log_buffer.clear()
    return {"message": "日志已清空"}
