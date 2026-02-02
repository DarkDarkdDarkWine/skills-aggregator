"""测试 AI Provider 服务"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.services.ai_provider import (
    AIProvider,
    BaseAIProvider,
    DeepSeekProvider,
    SiliconFlowProvider,
    AIProviderFactory,
    get_ai_provider,
)


class TestAIProviderBase:
    """测试 AI Provider 基础类"""

    @pytest.fixture
    def base_provider(self):
        """创建基础 Provider 实例"""
        return BaseAIProvider(
            api_key="test-key",
            base_url="https://api.test.com/v1",
            model="test-model",
            max_tokens=2048,
            temperature=0.1,
        )

    @pytest.mark.asyncio
    async def test_chat_success(self, base_provider):
        """测试聊天成功"""
        # Mock OpenAI 响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "测试回复"

        base_provider.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        messages = [{"role": "user", "content": "你好"}]
        result = await base_provider.chat(messages)

        assert result == "测试回复"
        base_provider.client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_success(self, base_provider):
        """测试分析成功"""
        # Mock JSON 响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "summary": "测试摘要",
                "quality_score": 85,
            }
        )

        base_provider.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        result = await base_provider.analyze("分析这个")

        assert result["summary"] == "测试摘要"
        assert result["quality_score"] == 85

    @pytest.mark.asyncio
    async def test_analyze_invalid_json(self, base_provider):
        """测试分析返回无效 JSON"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "这不是 JSON"

        base_provider.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(ValueError, match="AI response is not valid JSON"):
            await base_provider.analyze("分析这个")

    @pytest.mark.asyncio
    async def test_analyze_with_markdown(self, base_provider):
        """测试分析返回带 Markdown 的 JSON"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """```json
{"summary": "测试摘要"}
```"""

        base_provider.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        result = await base_provider.analyze("分析这个")
        assert result["summary"] == "测试摘要"


class TestDeepSeekProvider:
    """测试 DeepSeek Provider"""

    def test_initialization(self):
        """测试初始化"""
        provider = DeepSeekProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert "deepseek.com" in provider.base_url
        assert provider.model == "deepseek-chat"

    @pytest.mark.asyncio
    async def test_chat(self):
        """测试聊天"""
        provider = DeepSeekProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "回复内容"

        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [{"role": "user", "content": "测试"}]
        result = await provider.chat(messages)

        assert result == "回复内容"


class TestSiliconFlowProvider:
    """测试硅基流动 Provider"""

    def test_initialization(self):
        """测试初始化"""
        provider = SiliconFlowProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert "siliconflow.cn" in provider.base_url
        assert "DeepSeek-V3" in provider.model


class TestAIProviderFactory:
    """测试 Provider 工厂"""

    def teardown_method(self):
        """清理缓存"""
        AIProviderFactory._providers.clear()

    @patch("app.services.ai_provider.config")
    def test_get_deepseek_provider(self, mock_config):
        """测试获取 DeepSeek Provider"""
        mock_ai_config = MagicMock()
        mock_ai_config.active_provider = "deepseek"
        mock_ai_config.providers = {
            "deepseek": MagicMock(
                api_key="test-key",
                base_url="https://api.deepseek.com/v1",
                model="deepseek-chat",
            )
        }
        mock_config.ai = mock_ai_config

        provider = AIProviderFactory.get_provider("deepseek")

        assert isinstance(provider, DeepSeekProvider)
        assert provider.api_key == "test-key"

    @patch("app.services.ai_provider.config")
    def test_get_siliconflow_provider(self, mock_config):
        """测试获取硅基流动 Provider"""
        mock_ai_config = MagicMock()
        mock_ai_config.active_provider = "siliconflow"
        mock_ai_config.providers = {
            "siliconflow": MagicMock(
                api_key="sf-key",
                base_url="https://api.siliconflow.cn/v1",
                model="deepseek-ai/DeepSeek-V3",
            )
        }
        mock_config.ai = mock_ai_config

        provider = AIProviderFactory.get_provider("siliconflow")

        assert isinstance(provider, SiliconFlowProvider)

    @patch("app.services.ai_provider.config")
    def test_provider_caching(self, mock_config):
        """测试 Provider 缓存"""
        mock_ai_config = MagicMock()
        mock_ai_config.active_provider = "deepseek"
        mock_ai_config.providers = {
            "deepseek": MagicMock(
                api_key="test-key",
                base_url="https://api.deepseek.com/v1",
                model="deepseek-chat",
            )
        }
        mock_config.ai = mock_ai_config

        provider1 = AIProviderFactory.get_provider("deepseek")
        provider2 = AIProviderFactory.get_provider("deepseek")

        assert provider1 is provider2

    @patch("app.services.ai_provider.config")
    def test_unknown_provider(self, mock_config):
        """测试未知 Provider"""
        mock_ai_config = MagicMock()
        mock_ai_config.active_provider = "unknown"
        mock_ai_config.providers = {}
        mock_config.ai = mock_ai_config

        with pytest.raises(ValueError, match="Unknown AI provider"):
            AIProviderFactory.get_provider("unknown")
