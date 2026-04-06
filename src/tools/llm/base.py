"""
抽象 LLM 客户端接口定义
用于解耦具体的 LLM 实现，未来可以轻松切换千问、自定义模型等
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage


class LLMResponse:
    """LLM 响应封装"""
    def __init__(self, content: Any):
        self.content = content


class BaseLLMClient(ABC):
    """抽象 LLM 客户端接口"""
    
    @abstractmethod
    def invoke(
        self,
        messages: List[BaseMessage],
        model: str,
        temperature: float = 0.7,
        max_completion_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        调用 LLM
        
        Args:
            messages: 消息列表
            model: 模型 ID
            temperature: 温度参数
            max_completion_tokens: 最大生成 token 数
            **kwargs: 其他参数
            
        Returns:
            LLMResponse: LLM 响应
        """
        pass
