"""
充电桩智能客服工作流状态定义
"""
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ==================== 全局状态 ====================

class GlobalState(BaseModel):
    """全局状态定义 - 包含工作流执行过程中的所有数据"""
    user_message: str = Field(default="", description="用户发送的消息")
    intent: str = Field(default="", description="识别的意图类型：usage_guidance(使用指导), fault_handling(故障处理), complaint(投诉兜底)")
    knowledge_chunks: List[Dict[str, Any]] = Field(default=[], description="知识库搜索结果")
    user_info: Dict[str, str] = Field(default={}, description="收集的用户信息（手机号、订单号、问题描述等）")
    reply_content: str = Field(default="", description="回复给用户的内容")
    email_sent: bool = Field(default=False, description="邮件是否已发送")


# ==================== 图的输入输出 ====================

class GraphInput(BaseModel):
    """工作流的输入"""
    user_message: str = Field(..., description="用户发送的消息")


class GraphOutput(BaseModel):
    """工作流的输出"""
    reply_content: str = Field(..., description="回复给用户的内容")


# ==================== 意图识别节点 ====================

class IntentRecognitionInput(BaseModel):
    """意图识别节点的输入"""
    user_message: str = Field(..., description="用户发送的消息")


class IntentRecognitionOutput(BaseModel):
    """意图识别节点的输出"""
    intent: str = Field(..., description="识别的意图类型")


# ==================== 知识库问答节点 ====================

class KnowledgeQAInput(BaseModel):
    """知识库问答节点的输入"""
    user_message: str = Field(..., description="用户发送的消息")
    intent: str = Field(..., description="意图类型")


class KnowledgeQAOutput(BaseModel):
    """知识库问答节点的输出"""
    reply_content: str = Field(..., description="回复给用户的内容")
    knowledge_chunks: List[Dict[str, Any]] = Field(default=[], description="知识库搜索结果")


# ==================== 信息收集节点 ====================

class InfoCollectionInput(BaseModel):
    """信息收集节点的输入"""
    user_message: str = Field(..., description="用户发送的消息")


class InfoCollectionOutput(BaseModel):
    """信息收集节点的输出"""
    user_info: Dict[str, str] = Field(..., description="收集的用户信息")
    reply_content: str = Field(..., description="回复内容（提示用户已收到反馈）")


# ==================== 邮件发送节点 ====================

class EmailSendingInput(BaseModel):
    """邮件发送节点的输入"""
    user_info: Dict[str, str] = Field(..., description="收集的用户信息")
    user_message: str = Field(..., description="用户原始消息")


class EmailSendingOutput(BaseModel):
    """邮件发送节点的输出"""
    email_sent: bool = Field(..., description="邮件是否发送成功")
    reply_content: str = Field(..., description="回复内容")
