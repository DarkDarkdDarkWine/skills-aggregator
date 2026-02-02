from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Source(Base):
    """订阅源"""

    __tablename__ = "sources"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    priority = Column(Integer, default=0)
    sub_path = Column(String(500), default="")
    access_token = Column(String(500), nullable=True)
    last_commit = Column(String(100), nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    skill_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    skills = relationship("Skill", back_populates="source")


class Skill(Base):
    """技能"""

    __tablename__ = "skills"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False)
    path = Column(String(500), nullable=False)
    content_hash = Column(String(64), nullable=False)
    status = Column(String(20), default="ready")  # ready, blocked
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source = relationship("Source", back_populates="skills")
    analysis = relationship("SkillAnalysis", back_populates="skill", uselist=False)


class SkillAnalysis(Base):
    """技能分析结果"""

    __tablename__ = "skill_analyses"

    id = Column(String(36), primary_key=True)
    skill_id = Column(String(36), ForeignKey("skills.id"), unique=True, nullable=False)
    summary = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    use_cases = Column(JSON, default=list)
    triggers = Column(JSON, default=list)
    dependencies = Column(JSON, default=dict)
    quality_score = Column(Integer, default=0)
    quality_issues = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    skill = relationship("Skill", back_populates="analysis")


class Conflict(Base):
    """冲突"""

    __tablename__ = "conflicts"

    id = Column(String(36), primary_key=True)
    type = Column(String(50), nullable=False)  # name_conflict, similar_conflict
    skill_ids = Column(JSON, default=list)  # 相关的 Skill IDs
    skill_hashes = Column(
        JSON, default=dict
    )  # {skill_id: content_hash} 记录决策时的版本
    ai_recommendation = Column(JSON, default=dict)  # AI 推荐
    status = Column(String(20), default="pending")  # pending, resolved, auto_reused
    resolution = Column(JSON, nullable=True)  # 用户决策
    resolved_at = Column(DateTime, nullable=True)
    reused_from = Column(String(36), nullable=True)  # 如果是自动沿用，记录原决策 ID
    created_at = Column(DateTime, default=datetime.utcnow)


class MergedSkill(Base):
    """合并记录"""

    __tablename__ = "merged_skills"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    source_skill_ids = Column(JSON, default=list)  # 合并来源
    content = Column(Text, nullable=True)  # 合并后的 SKILL.md
    scripts = Column(JSON, default=list)  # 合并后的脚本文件
    created_at = Column(DateTime, default=datetime.utcnow)


class RenamingRecord(Base):
    """重命名追踪记录"""

    __tablename__ = "renaming_records"

    id = Column(String(36), primary_key=True)
    original_filename = Column(String(255), nullable=False)  # 原始文件名
    assigned_filename = Column(String(255), nullable=False)  # 分配后的文件名
    source_repo = Column(String(255), nullable=False)  # 来源仓库
    skill_id = Column(String(36), nullable=False)  # 所属 Skill
    file_hash = Column(String(64), nullable=False)  # 文件内容 hash
    reasoning = Column(Text, nullable=True)  # AI 重命名的理由
    created_at = Column(DateTime, default=datetime.utcnow)


class DecisionHistory(Base):
    """决策历史"""

    __tablename__ = "decision_histories"

    id = Column(String(36), primary_key=True)
    conflict_type = Column(String(50), nullable=False)
    skill_ids = Column(JSON, default=list)
    skill_hashes = Column(JSON, default=dict)  # 决策时的 content hash
    decision = Column(JSON, nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SyncLog(Base):
    """同步日志"""

    __tablename__ = "sync_logs"

    id = Column(String(36), primary_key=True)
    action = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")  # pending, running, success, failed
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
