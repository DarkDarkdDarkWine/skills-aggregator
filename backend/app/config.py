import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field


class AIProviderConfig(BaseModel):
    """AI Provider 配置"""

    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4"
    max_tokens: int = 4096
    temperature: float = 0.1


class AIConfig(BaseModel):
    """AI 配置"""

    active_provider: str = "deepseek"
    providers: Dict[str, AIProviderConfig] = Field(default_factory=dict)
    max_tokens: int = 4096
    temperature: float = 0.1


class DatabaseConfig(BaseModel):
    """数据库配置"""

    url: str = (
        "postgresql://skills_aggregator:skills2024@192.168.31.14:5433/skills_aggregator"
    )


class StorageConfig(BaseModel):
    """存储配置"""

    sources_dir: str = "./data/sources"
    output_dir: str = "./data/output"
    analysis_cache_dir: str = "./data/analysis"


class OutputConfig(BaseModel):
    """输出配置"""

    mode: str = "single"
    paths: Dict[str, Any] = Field(default_factory=dict)


class StatusAPIConfig(BaseModel):
    """状态 API 配置"""

    include_ready_count: bool = True
    include_blocked_count: bool = True
    include_blocked_skills: bool = False


class Config:
    """配置管理"""

    def __init__(self):
        self.config_path = self._find_config_file()
        self._config = self._load_config()

    def _find_config_file(self) -> Path:
        """查找配置文件"""
        possible_paths = [
            Path("./config.yaml"),
            Path(__file__).parent.parent.parent / "config.yaml",
            Path("/app/config.yaml"),
        ]

        for path in possible_paths:
            if path.exists():
                return path

        raise FileNotFoundError("config.yaml not found")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def ai(self) -> AIConfig:
        """获取 AI 配置"""
        raw_ai = self._config.get("ai", {})
        providers = {}

        for name, config in raw_ai.get("providers", {}).items():
            if name == "active_provider":
                continue
            providers[name] = AIProviderConfig(**config)

        return AIConfig(
            active_provider=raw_ai.get("active_provider", "deepseek"),
            providers=providers,
            max_tokens=raw_ai.get("max_tokens", 4096),
            temperature=raw_ai.get("temperature", 0.1),
        )

    @property
    def database(self) -> DatabaseConfig:
        """获取数据库配置"""
        return DatabaseConfig(**self._config.get("database", {}))

    @property
    def storage(self) -> StorageConfig:
        """获取存储配置"""
        return StorageConfig(**self._config.get("storage", {}))

    @property
    def output(self) -> OutputConfig:
        """获取输出配置"""
        return OutputConfig(**self._config.get("output", {}))

    @property
    def status_api(self) -> StatusAPIConfig:
        """获取状态 API 配置"""
        return StatusAPIConfig(**self._config.get("status_api", {}))

    @property
    def blacklist(self) -> list:
        """获取黑名单"""
        return self._config.get("blacklist", [])

    @property
    def whitelist(self) -> list:
        """获取白名单"""
        return self._config.get("whitelist", [])

    def get_sources(self) -> list:
        """获取订阅源列表"""
        return self._config.get("sources", [])


# 全局配置实例
config = Config()
