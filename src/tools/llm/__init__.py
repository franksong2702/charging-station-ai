"""
LLM 客户端工厂
用于根据配置创建不同的 LLM 客户端
"""
from typing import Optional
from coze_coding_utils.runtime_ctx.context import Context

from .base import BaseLLMClient
from .doubao import DoubaoLLMClient


def create_llm_client(
    ctx: Context,
    provider: str = "doubao"
) -> BaseLLMClient:
    """
    创建 LLM 客户端
    
    Args:
        ctx: 上下文对象
        provider: LLM 提供商，目前支持 "doubao"
        
    Returns:
        BaseLLMClient: LLM 客户端实例
    """
    if provider == "doubao":
        return DoubaoLLMClient(ctx=ctx)
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")


__all__ = [
    "BaseLLMClient",
    "LLMResponse",
    "DoubaoLLMClient",
    "create_llm_client"
]
