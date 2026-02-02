from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json
import logging

import httpx
from openai import AsyncOpenAI

from ..config import config

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """AI Provider 抽象基类"""

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """发送对话请求"""
        pass

    @abstractmethod
    async def analyze(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """发送分析请求"""
        pass


class BaseAIProvider(AIProvider):
    """AI Provider 基础类"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.AsyncClient(timeout=120.0),
        )

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """发送对话请求"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI API error: {e}")
            raise

    async def analyze(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """发送分析请求"""
        messages = [{"role": "user", "content": prompt}]
        response = await self.chat(messages, **kwargs)

        # 尝试解析 JSON
        try:
            # 清理可能的 markdown 代码块
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Raw response: {response}")
            raise ValueError("AI response is not valid JSON")


class DeepSeekProvider(BaseAIProvider):
    """DeepSeek Provider"""

    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
            max_tokens=4096,
            temperature=0.1,
        )


class SiliconFlowProvider(BaseAIProvider):
    """硅基流动 Provider"""

    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url="https://api.siliconflow.cn/v1",
            model="deepseek-ai/DeepSeek-V3",
            max_tokens=4096,
            temperature=0.1,
        )


class AIProviderFactory:
    """AI Provider 工厂"""

    _providers: Dict[str, AIProvider] = {}

    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None) -> AIProvider:
        """获取 Provider 实例"""
        if provider_name is None:
            provider_name = config.ai.active_provider

        if provider_name in cls._providers:
            return cls._providers[provider_name]

        ai_config = config.ai.providers.get(provider_name)
        if not ai_config:
            raise ValueError(f"Unknown AI provider: {provider_name}")

        provider: AIProvider
        if provider_name == "deepseek":
            provider = DeepSeekProvider(api_key=ai_config.api_key)
        elif provider_name == "siliconflow":
            provider = SiliconFlowProvider(api_key=ai_config.api_key)
        else:
            raise ValueError(f"Unsupported AI provider: {provider_name}")

        cls._providers[provider_name] = provider
        return provider

    @classmethod
    def clear_cache(cls):
        """清除缓存的 Provider 实例"""
        cls._providers.clear()


# 全局 Provider 实例
_ai_provider: Optional[AIProvider] = None


def get_ai_provider() -> AIProvider:
    """获取 AI Provider 实例"""
    global _ai_provider
    if _ai_provider is None:
        _ai_provider = AIProviderFactory.get_provider()
    return _ai_provider
