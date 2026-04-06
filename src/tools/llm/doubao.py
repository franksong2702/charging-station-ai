"""
豆包 LLM 客户端实现
基于 coze_coding_dev_sdk 的 LLMClient
"""
from typing import List, Optional
from langchain_core.messages import BaseMessage
from coze_coding_dev_sdk import LLMClient as CozeLLMClient
from coze_coding_utils.runtime_ctx.context import Context

from .base import BaseLLMClient, LLMResponse


class DoubaoLLMClient(BaseLLMClient):
    """豆包 LLM 客户端实现"""
    
    def __init__(self, ctx: Context):
        """
        初始化豆包 LLM 客户端
        
        Args:
            ctx: 上下文对象
        """
        self._client = CozeLLMClient(ctx=ctx)
    
    def invoke(
        self,
        messages: List[BaseMessage],
        model: str,
        temperature: float = 0.7,
        max_completion_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        调用豆包 LLM
        
        Args:
            messages: 消息列表
            model: 模型 ID
            temperature: 温度参数
            max_completion_tokens: 最大生成 token 数
            **kwargs: 其他参数
            
        Returns:
            LLMResponse: LLM 响应
        """
        # 构建调用参数
        invoke_kwargs = {
            "messages": messages,
            "model": model,
            "temperature": temperature
        }
        
        if max_completion_tokens is not None:
            invoke_kwargs["max_completion_tokens"] = max_completion_tokens
        
        # 添加其他参数
        invoke_kwargs.update(kwargs)
        
        # 调用豆包 SDK
        response = self._client.invoke(**invoke_kwargs)
        
        # 封装响应
        return LLMResponse(content=response.content)
