"""
充电桩智能客服工作流状态定义
支持文字和语音输入，支持评价机制，支持多轮对话
"""
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== 全局状态 ====================

class GlobalState(BaseModel):
    """全局状态定义 - 包含工作流执行过程中的所有数据"""
    user_message: str = Field(default="", description="用户发送的消息（文字或语音转写后的文字）")
    voice_url: str = Field(default="", description="用户发送的语音URL（可选）")
    user_id: str = Field(default="", description="用户身份标识（企业微信 external_userid，用于多轮对话）")
    intent: str = Field(default="", description="识别的意图类型：usage_guidance(使用指导), fault_handling(故障处理), complaint(投诉兜底), feedback(评价反馈)")
    knowledge_chunks: List[Dict[str, Any]] = Field(default=[], description="知识库搜索结果")
    user_info: Dict[str, str] = Field(default={}, description="收集的用户信息（手机号、订单号、问题描述等）")
    reply_content: str = Field(default="", description="回复给用户的内容")
    email_sent: bool = Field(default=False, description="邮件是否已发送")
    feedback_type: str = Field(default="", description="评价类型：good(很好), bad(没有帮助)")
    need_feedback: bool = Field(default=False, description="是否需要请求用户评价")
    conversation_history: List[Dict[str, str]] = Field(default=[], description="对话历史记录（用于多轮对话上下文）")


# ==================== 图的输入输出 ====================

class GraphInput(BaseModel):
    """工作流的输入"""
    user_message: str = Field(default="", description="用户发送的文字消息")
    voice_url: str = Field(default="", description="用户发送的语音URL（可选，如来自微信语音消息）")
    user_id: str = Field(default="", description="用户身份标识（企业微信 external_userid，可选，用于多轮对话）")


class GraphOutput(BaseModel):
    """工作流的输出"""
    reply_content: str = Field(..., description="回复给用户的内容")


# ==================== 输入预处理节点 ====================

class InputProcessInput(BaseModel):
    """输入预处理节点的输入"""
    user_message: str = Field(default="", description="用户发送的文字消息")
    voice_url: str = Field(default="", description="用户发送的语音URL")


class InputProcessOutput(BaseModel):
    """输入预处理节点的输出"""
    processed: bool = Field(default=True, description="是否已处理")


# ==================== ASR 语音转文字节点 ====================

class ASRInput(BaseModel):
    """ASR节点的输入"""
    voice_url: str = Field(..., description="语音文件的URL")


class ASROutput(BaseModel):
    """ASR节点的输出"""
    user_message: str = Field(..., description="语音转写的文字内容")


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
    conversation_history: List[Dict[str, str]] = Field(default=[], description="对话历史记录（用于多轮对话上下文）")


class KnowledgeQAOutput(BaseModel):
    """知识库问答节点的输出"""
    reply_content: str = Field(..., description="回复给用户的内容")
    knowledge_chunks: List[Dict[str, Any]] = Field(default=[], description="知识库搜索结果")
    need_feedback: bool = Field(default=False, description="是否需要请求用户评价（由LLM智能判断）")


# ==================== 评价反馈节点 ====================

class FeedbackInput(BaseModel):
    """评价反馈节点的输入"""
    user_message: str = Field(..., description="用户发送的评价消息")


class FeedbackOutput(BaseModel):
    """评价反馈节点的输出"""
    feedback_type: str = Field(..., description="评价类型：good(很好), bad(没有帮助)")
    reply_content: str = Field(..., description="回复内容")


# ==================== 记录保存节点 ====================

class SaveRecordInput(BaseModel):
    """记录保存节点的输入"""
    user_id: str = Field(default="", description="用户身份标识（可选）")
    user_message: str = Field(default="", description="用户发送的消息")
    reply_content: str = Field(default="", description="AI回复内容")
    intent: str = Field(default="", description="意图类型")
    feedback_type: str = Field(default="", description="评价类型")
    knowledge_chunks: List[Dict[str, Any]] = Field(default=[], description="知识库搜索结果")


class SaveRecordOutput(BaseModel):
    """记录保存节点的输出"""
    saved: bool = Field(default=True, description="是否保存成功")


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


# ==================== 加载对话历史节点 ====================

class LoadHistoryInput(BaseModel):
    """加载对话历史节点的输入"""
    user_id: str = Field(default="", description="用户身份标识（可选）")


class LoadHistoryOutput(BaseModel):
    """加载对话历史节点的输出"""
    conversation_history: List[Dict[str, str]] = Field(default=[], description="对话历史记录")


# ==================== 保存对话历史节点 ====================

class SaveHistoryInput(BaseModel):
    """保存对话历史节点的输入"""
    user_id: str = Field(default="", description="用户身份标识（可选）")
    user_message: str = Field(default="", description="用户发送的消息")
    reply_content: str = Field(default="", description="AI回复内容")
    intent: str = Field(default="", description="意图类型")


class SaveHistoryOutput(BaseModel):
    """保存对话历史节点的输出"""
    saved: bool = Field(default=True, description="是否保存成功")


# ==================== 不满意处理节点 ====================

class DissatisfiedInput(BaseModel):
    """不满意处理节点的输入"""
    user_message: str = Field(..., description="用户发送的消息")


class DissatisfiedOutput(BaseModel):
    """不满意处理节点的输出"""
    reply_content: str = Field(..., description="回复内容")
    dissatisfied_logged: bool = Field(default=True, description="是否已记录不满意")
