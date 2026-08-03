"""
LLM 配置模块 - 支持多种 Provider
"""

import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class LLMProvider(Enum):
    """LLM Provider 枚举"""
    OPENAI = "openai"
    MIMO = "mimo"
    MINIMAX = "minimax"
    ANTHROPIC = "anthropic"
    ZHIPU = "zhipu"


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: LLMProvider = LLMProvider.MIMO
    model_name: str = "mimo-v2.5-pro"
    temperature: float = 0.7
    base_url: Optional[str] = None
    api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """从环境变量加载配置"""
        provider_name = os.getenv("LLM_PROVIDER", "mimo").lower()

        if provider_name == "openai":
            provider = LLMProvider.OPENAI
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            api_key = os.getenv("OPENAI_API_KEY")
        elif provider_name == "anthropic":
            provider = LLMProvider.ANTHROPIC
            model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6-20250514")
            base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
            api_key = os.getenv("ANTHROPIC_API_KEY")
        elif provider_name == "zhipu":
            provider = LLMProvider.ZHIPU
            model = os.getenv("ZHIPU_MODEL", "glm-5.2")
            base_url = os.getenv("ZHIPU_BASE_URL", "https://yuanyuaicloud.cn/v1")
            api_key = os.getenv("ZHIPU_API_KEY")
        elif provider_name == "minimax":
            provider = LLMProvider.MINIMAX
            model = os.getenv("MINIMAX_MODEL", "MiniMax-M3")
            base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1")
            api_key = os.getenv("MINIMAX_API_KEY")
        else:
            # MiMo (default)
            provider = LLMProvider.MIMO
            model = os.getenv("MIMO_MODEL", "mimo-v2.5-pro")
            base_url = os.getenv("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1")
            api_key = os.getenv("MIMO_API_KEY")

        return cls(
            provider=provider,
            model_name=model,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            base_url=base_url,
            api_key=api_key
        )


# 全局配置实例
_config: Optional[LLMConfig] = None


def get_llm_config() -> LLMConfig:
    """获取 LLM 配置（单例）"""
    global _config
    if _config is None:
        _config = LLMConfig.from_env()
    return _config


def reset_llm_config():
    """重置 LLM 配置"""
    global _config
    _config = None