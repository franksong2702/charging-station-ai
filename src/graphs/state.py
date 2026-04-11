"""
充电桩智能客服工作流状态定义
支持评价机制，支持多轮对话
"""
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== 全局状态 ====================

class GlobalState(BaseModel):
    """全局状态定义 - 包含工作流执行过程中的所有数据"""
    user_message: str = Field(default="", description="用户发送的消息")
    user_id: str = Field(default="", description="用户身份标识（企业微信 external_userid，用于多轮对话）")
    intent: str = Field(default="", description="识别的意图类型")
    rewritten_query: str = Field(default="", description="LLM 改写后的搜索词（更精准）")
    knowledge_chunks: List[Dict[str, Any]] = Field(default=[], description="知识库搜索结果")
    knowledge_missed: bool = Field(default=False, description="知识库是否没有覆盖到这个问题（用于后续知识库扩充）")
    user_info: Dict[str, str] = Field(default={}, description="收集的用户信息（手机号、车牌号等）")
    reply_content: str = Field(default="", description="回复给用户的内容")
    email_sent: bool = Field(default=False, description="邮件是否已发送")
    feedback_type: str = Field(default="", description="评价类型：good(很好), bad(没有帮助)")
    need_feedback: bool = Field(default=False, description="是否需要请求用户评价")
    conversation_history: List[Dict[str, str]] = Field(default=[], description="对话历史记录（用于多轮对话上下文）")
    # 兜底流程相关
    fallback_phase: str = Field(default="", description="兜底流程阶段：ask_problem/collect_info/confirm/send")
    phone: str = Field(default="", description="用户手机号")
    license_plate: str = Field(default="", description="用户车牌号")
    problem_summary: str = Field(default="", description="问题总结（AI 生成）")
    user_supplement: str = Field(default="", description="用户补充内容")
    entry_problem: str = Field(default="", description="用户进入兜底流程时的问题描述")
    case_confirmed: bool = Field(default=False, description="用户是否已确认问题总结")
    case_created: bool = Field(default=False, description="工单是否已创建")
    # 协商处理相关
    negotiate_phase: str = Field(default="", description="协商处理阶段：asking/proposing/confirming/escalating")
    problem_understanding: str = Field(default="", description="对用户问题的理解")
    negotiate_round_count: int = Field(default=0, description="协商轮数计数")
    # 路由标记：用于 save_history 之后判断去哪个分支
    route_after_save: str = Field(default="", description="save_history 之后的路由标记：save_record/cond_fallback/cond_negotiate")


# ==================== 图的输入输出 ====================

class GraphInput(BaseModel):
    """工作流的输入"""
    user_message: str = Field(default="", description="用户发送的文字消息")
    user_id: str = Field(default="", description="用户身份标识（企业微信 external_userid，可选，用于多轮对话）")
    # 兜底流程状态（用于多轮对话）
    fallback_phase: str = Field(default="", description="兜底流程阶段（可选）")
    phone: str = Field(default="", description="已收集的手机号（可选）")
    license_plate: str = Field(default="", description="已收集的车牌号（可选）")
    problem_summary: str = Field(default="", description="已生成的问题总结（可选）")
    user_supplement: str = Field(default="", description="用户补充内容（可选）")
    entry_problem: str = Field(default="", description="用户进入兜底流程时的问题描述（可选）")


class GraphOutput(BaseModel):
    """工作流的输出"""
    reply_content: str = Field(..., description="回复给用户的内容")


# ==================== 意图识别节点 ====================

class IntentRecognitionInput(BaseModel):
    """意图识别节点的输入"""
    user_message: str = Field(..., description="用户发送的消息")
    fallback_phase: str = Field(default="", description="兜底流程阶段（非空表示正在兜底流程中）")
    problem_summary: str = Field(default="", description="已生成的问题总结（兜底流程确认阶段使用）")
    entry_problem: str = Field(default="", description="用户进入兜底流程时的问题描述")


class IntentRecognitionOutput(BaseModel):
    """意图识别节点的输出"""
    intent: str = Field(..., description="识别的意图类型")


# ==================== 查询改写节点 ====================

class QueryRewriteInput(BaseModel):
    """查询改写节点的输入"""
    user_message: str = Field(..., description="用户发送的消息")
    intent: str = Field(..., description="识别的意图类型")


class QueryRewriteOutput(BaseModel):
    """查询改写节点的输出"""
    rewritten_query: str = Field(..., description="改写后的搜索词（更精准）")


# ==================== 知识库问答节点 ====================

class KnowledgeQAInput(BaseModel):
    """知识库问答节点的输入"""
    user_message: str = Field(..., description="用户发送的消息")
    rewritten_query: str = Field(default="", description="LLM 改写后的搜索词")
    intent: str = Field(..., description="意图类型")
    conversation_history: List[Dict[str, str]] = Field(default=[], description="对话历史记录（用于多轮对话上下文）")


class KnowledgeQAOutput(BaseModel):
    """知识库问答节点的输出"""
    reply_content: str = Field(..., description="回复给用户的内容")
    knowledge_chunks: List[Dict[str, Any]] = Field(default=[], description="知识库搜索结果")
    need_feedback: bool = Field(default=False, description="是否需要请求用户评价（由 LLM 智能判断）")
    knowledge_missed: bool = Field(default=False, description="知识库是否没有覆盖到这个问题（用于后续知识库扩充）")


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
    reply_content: str = Field(default="", description="AI 回复内容")
    intent: str = Field(default="", description="意图类型")
    feedback_type: str = Field(default="", description="评价类型")
    knowledge_chunks: List[Dict[str, Any]] = Field(default=[], description="知识库搜索结果")
    knowledge_missed: bool = Field(default=False, description="知识库是否没有覆盖到这个问题（用于后续知识库扩充）")
    conversation_history: List[Dict[str, str]] = Field(default=[], description="对话历史（用于评价时保存完整上下文）")


class SaveRecordOutput(BaseModel):
    """记录保存节点的输出"""
    saved: bool = Field(default=True, description="是否保存成功")


# ==================== 邮件发送节点 ====================

class EmailSendingInput(BaseModel):
    """邮件发送节点的输入"""
    user_id: str = Field(default="", description="用户身份标识")
    user_message: str = Field(default="", description="用户原始消息")
    user_info: Dict[str, str] = Field(default={}, description="收集的用户信息（旧格式，兼容）")
    # 兜底流程数据
    phone: str = Field(default="", description="用户手机号")
    license_plate: str = Field(default="", description="用户车牌号")
    problem_summary: str = Field(default="", description="问题总结")
    case_id: str = Field(default="", description="工单 ID")
    # 完整对话历史
    conversation_history: List[Dict[str, str]] = Field(default=[], description="完整对话记录（用户+AI）")
    # 截断索引：只展示这个索引之后的对话（这次投诉的对话）
    conversation_truncate_index: Optional[int] = Field(default=None, description="对话截断索引，用于邮件中只展示投诉相关的对话")
    reply_content: str = Field(default="", description="要保留的回复内容")


class EmailSendingOutput(BaseModel):
    """邮件发送节点的输出"""
    email_sent: bool = Field(..., description="邮件是否发送成功")
    reply_content: str = Field(..., description="回复内容")


# ==================== 加载对话历史节点 ====================

class LoadHistoryInput(BaseModel):
    """加载对话历史节点的输入"""
    user_id: str = Field(default="", description="用户身份标识（可选）")
    # GraphInput 中传入的兜底流程状态（优先使用）
    fallback_phase: str = Field(default="", description="兜底流程阶段（来自 GraphInput）")
    phone: str = Field(default="", description="手机号（来自 GraphInput）")
    license_plate: str = Field(default="", description="车牌号（来自 GraphInput）")
    problem_summary: str = Field(default="", description="问题总结（来自 GraphInput）")
    entry_problem: str = Field(default="", description="用户问题描述（来自 GraphInput）")


class LoadHistoryOutput(BaseModel):
    """加载对话历史节点的输出"""
    conversation_history: List[Dict[str, str]] = Field(default=[], description="对话历史记录")
    # 兜底流程状态
    fallback_phase: str = Field(default="", description="兜底流程阶段")
    phone: str = Field(default="", description="用户手机号")
    license_plate: str = Field(default="", description="用户车牌号")
    problem_summary: str = Field(default="", description="问题总结")
    entry_problem: str = Field(default="", description="用户问题描述")


# ==================== 保存对话历史节点 ====================

class SaveHistoryInput(BaseModel):
    """保存对话历史节点的输入"""
    user_id: str = Field(default="", description="用户身份标识（可选）")
    user_message: str = Field(default="", description="用户发送的消息")
    reply_content: str = Field(default="", description="AI 回复内容")
    intent: str = Field(default="", description="意图类型")
    # 兜底流程状态
    fallback_phase: str = Field(default="", description="兜底流程阶段")
    phone: str = Field(default="", description="用户手机号")
    license_plate: str = Field(default="", description="用户车牌号")
    problem_summary: str = Field(default="", description="问题总结")
    entry_problem: str = Field(default="", description="用户问题描述")
    user_supplement: str = Field(default="", description="用户补充内容")


class SaveHistoryOutput(BaseModel):
    """保存对话历史节点的输出"""
    saved: bool = Field(default=True, description="是否保存成功")


# ==================== 不满意处理节点 ====================

class DissatisfiedInput(BaseModel):
    """不满意处理节点的输入（轻度不满）"""
    user_message: str = Field(..., description="用户发送的消息")
    conversation_history: List[Dict[str, str]] = Field(default=[], description="对话历史记录")


class DissatisfiedOutput(BaseModel):
    """不满意处理节点的输出（轻度不满）"""
    reply_content: str = Field(..., description="回复内容")
    dissatisfied_logged: bool = Field(default=True, description="是否已记录不满意")


# ==================== 满意处理节点 ====================

class SatisfiedInput(BaseModel):
    """满意处理节点的输入"""
    user_message: str = Field(..., description="用户发送的消息")


class SatisfiedOutput(BaseModel):
    """满意处理节点的输出"""
    reply_content: str = Field(..., description="回复内容")
    satisfied_logged: bool = Field(default=True, description="是否已记录满意")


# ==================== 兜底流程节点 ====================

class FallbackInput(BaseModel):
    """兜底流程节点的输入"""
    user_message: str = Field(..., description="用户发送的消息")
    conversation_history: List[Dict[str, str]] = Field(default=[], description="对话历史记录")
    fallback_phase: str = Field(default="collect_info", description="当前阶段")
    phone: str = Field(default="", description="已收集的手机号")
    license_plate: str = Field(default="", description="已收集的车牌号")
    problem_summary: str = Field(default="", description="已生成的问题总结")
    user_supplement: str = Field(default="", description="用户补充内容")
    entry_problem: str = Field(default="", description="用户进入兜底流程时的问题描述")
    # 截断索引：只展示这个索引之后的对话（这次投诉的对话）
    conversation_truncate_index: Optional[int] = Field(default=None, description="对话截断索引，用于邮件中只展示投诉相关的对话")


class FallbackOutput(BaseModel):
    """兜底流程节点的输出"""
    reply_content: str = Field(..., description="回复内容")
    fallback_phase: str = Field(..., description="下一阶段")
    phone: str = Field(default="", description="收集的手机号")
    license_plate: str = Field(default="", description="收集的车牌号")
    problem_summary: str = Field(default="", description="问题总结")
    user_supplement: str = Field(default="", description="用户补充内容")
    entry_problem: str = Field(default="", description="用户进入兜底流程时的问题描述")
    case_confirmed: bool = Field(default=False, description="用户是否已确认")
    # 截断索引：只展示这个索引之后的对话（这次投诉的对话）
    conversation_truncate_index: Optional[int] = Field(default=None, description="对话截断索引，用于邮件中只展示投诉相关的对话")


# ==================== 创建工单节点 ====================

class CreateCaseInput(BaseModel):
    """创建工单节点的输入"""
    user_id: str = Field(default="", description="用户身份标识")
    phone: str = Field(..., description="用户手机号")
    license_plate: str = Field(default="", description="用户车牌号")
    problem_summary: str = Field(..., description="问题总结")
    conversation_history: List[Dict[str, str]] = Field(default=[], description="完整对话上下文")
    reply_content: str = Field(default="", description="要保留的回复内容")


class CreateCaseOutput(BaseModel):
    """创建工单节点的输出"""
    case_created: bool = Field(default=True, description="工单是否创建成功")
    case_id: str = Field(default="", description="工单 ID")
    reply_content: str = Field(default="", description="保留的回复内容")


# ==================== 清除兜底状态节点 ====================

class ClearFallbackStateInput(BaseModel):
    """清除兜底状态节点的输入"""
    user_id: str = Field(default="", description="用户身份标识")
    user_message: str = Field(default="", description="用户消息")
    reply_content: str = Field(default="", description="AI 回复内容")
    case_confirmed: bool = Field(default=False, description="是否已确认工单（用于路由判断）")


class ClearFallbackStateOutput(BaseModel):
    """清除兜底状态节点的输出"""
    cleared: bool = Field(default=True, description="是否清除成功")
    fallback_phase: str = Field(default="", description="清空后的兜底阶段（空字符串）")
    phone: str = Field(default="", description="清空后的手机号")
    license_plate: str = Field(default="", description="清空后的车牌号")
    problem_summary: str = Field(default="", description="清空后的问题总结")
    case_confirmed: bool = Field(default=False, description="重置确认状态")
    intent: str = Field(default="usage_guidance", description="重置为默认意图")
    reply_content: str = Field(default="", description="给用户的友好回复内容")


# ==================== 条件判断节点输入类型 ====================

class IntentRouteCheck(BaseModel):
    """意图路由的条件输入"""
    intent: str = Field(default="", description="识别的意图类型")


class CaseConfirmedCheck(BaseModel):
    """工单确认判断的条件输入"""
    case_confirmed: bool = Field(default=False, description="用户是否已确认问题总结")


# ==================== 协商处理节点 ====================

class NegotiateInput(BaseModel):
    """协商处理节点的输入"""
    user_message: str = Field(..., description="用户发送的消息")
    conversation_history: List[Dict[str, str]] = Field(default=[], description="对话历史记录")


class NegotiateOutput(BaseModel):
    """协商处理节点的输出"""
    reply_content: str = Field(..., description="回复给用户的内容")
    negotiate_phase: str = Field(default="asking", description="协商阶段：asking(追问)/proposing(给方案)/confirming(确认)")
    problem_understanding: str = Field(default="", description="对用户问题的理解")
    route_after_save: str = Field(default="save_record", description="save_history 之后的路由：save_record/cond_fallback")


# ==================== Summary Agent 节点 ====================

class SummaryInput(BaseModel):
    """Summary Agent 节点的输入"""
    conversation_history: List[Dict[str, str]] = Field(..., description="对话历史记录")


class SummaryOutput(BaseModel):
    """Summary Agent 节点的输出"""
    detailed_summary: str = Field(..., description="详细总结（包含原因）")
    simple_problem: str = Field(default="", description="简单问题描述")


# ==================== 协商处理条件节点输入类型 ====================

class NegotiateRouteCheck(BaseModel):
    """协商处理路由的条件输入"""
    user_message: str = Field(default="", description="用户发送的消息")


class AfterSaveRouteCheck(BaseModel):
    """save_history 之后路由检查的输入"""
    route_after_save: str = Field(default="", description="路由标记：save_record/cond_fallback/cond_negotiate")
    # 兜底流程相关
    case_confirmed: bool = Field(default=False, description="用户是否已确认问题总结")
    # 协商处理相关
    user_message: str = Field(default="", description="用户消息（用于协商处理路由判断）")
