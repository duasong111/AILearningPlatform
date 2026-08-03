import os

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from ..config import LLMProvider, get_llm_config
from ..reasoning_patch import apply_reasoning_content_patch


def build_llm(
    *,
    streaming: bool = True,
    temperature: float | None = None,
    enable_thinking: bool = False,
    provider: LLMProvider | None = None,
    max_tokens: int | None = None,
):
    """构建 LLM 实例。

    Args:
        streaming: 是否启用流式输出
        temperature: 生成温度
        enable_thinking: 是否启用思考模式（部分模型支持）
        provider: 强制指定 provider，None 时使用配置
        max_tokens: 最大生成 token 数，None 时不限制

    Returns:
        LangChain ChatModel 实例
    """
    config = get_llm_config()
    effective_provider = provider or config.provider
    model_temperature = config.temperature if temperature is None else temperature
    apply_reasoning_content_patch()
    thinking_config = {"thinking": {"type": "enabled" if enable_thinking else "disabled"}}

    # 默认 max_tokens 限制，避免响应过长导致响应时间过长
    # 概念解释类问题通常 2000 tokens 足够
    effective_max_tokens = max_tokens if max_tokens is not None else 4000

    if effective_provider == LLMProvider.MIMO:
        return ChatOpenAI(
            model=config.model_name,
            temperature=model_temperature,
            api_key=config.api_key,
            base_url=config.base_url,
            default_headers={"api-key": config.api_key},
            max_retries=1,
            streaming=streaming,
            max_tokens=effective_max_tokens,
            extra_body=thinking_config,
        )
    if effective_provider == LLMProvider.ZHIPU:
        return ChatOpenAI(
            model=config.model_name,
            temperature=model_temperature,
            api_key=config.api_key,
            base_url=config.base_url,
            max_retries=1,
            streaming=streaming,
        )
    if effective_provider == LLMProvider.MINIMAX:
        # MiniMax API，使用独立的 MiniMax 凭据
        model = os.getenv("MINIMAX_MODEL", "MiniMax-M3")
        base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1")
        api_key = os.getenv("MINIMAX_API_KEY", config.api_key)
        return ChatOpenAI(
            model=model,
            temperature=model_temperature,
            api_key=api_key,
            base_url=base_url,
            max_retries=1,
            streaming=streaming,
            max_tokens=effective_max_tokens,
        )
    if effective_provider == LLMProvider.ANTHROPIC:
        return ChatAnthropic(
            model=config.model_name,
            temperature=model_temperature,
            api_key=config.api_key,
            base_url=config.base_url,
            max_retries=1,
            streaming=streaming,
            max_tokens=effective_max_tokens,
        )
    return ChatOpenAI(
        model=config.model_name,
        temperature=model_temperature,
        api_key=config.api_key,
        base_url=config.base_url,
        max_retries=1,
        streaming=streaming,
        max_tokens=effective_max_tokens,
        extra_body=thinking_config,
    )