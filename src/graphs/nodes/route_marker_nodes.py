"""
路由标记节点 - 用于在 save_history 之前设置 route_after_save 字段
注意：保留已有的 reply_content 等字段，不要覆盖！
"""
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from pydantic import BaseModel, Field
from typing import Optional


class RouteMarkerInput(BaseModel):
    """路由标记节点的输入 - 包含需要保留的字段"""
    reply_content: str = Field(default="", description="需要保留的回复内容")
    # 兜底流程相关
    fallback_phase: str = Field(default="", description="兜底流程阶段")
    phone: str = Field(default="", description="手机号")
    license_plate: str = Field(default="", description="车牌号")
    problem_summary: str = Field(default="", description="问题总结")
    user_supplement: str = Field(default="", description="用户补充")
    entry_problem: str = Field(default="", description="用户问题描述")
    case_confirmed: bool = Field(default=False, description="是否已确认")
    conversation_truncate_index: Optional[int] = Field(default=None, description="对话截断索引")


class RouteMarkerOutput(BaseModel):
    """路由标记节点的输出 - 保留所有输入字段，只添加 route_after_save"""
    route_after_save: str = Field(..., description="save_history 之后的路由标记")
    # 保留的字段
    reply_content: str = Field(default="", description="回复内容")
    fallback_phase: str = Field(default="", description="兜底流程阶段")
    phone: str = Field(default="", description="手机号")
    license_plate: str = Field(default="", description="车牌号")
    problem_summary: str = Field(default="", description="问题总结")
    user_supplement: str = Field(default="", description="用户补充")
    entry_problem: str = Field(default="", description="用户问题描述")
    case_confirmed: bool = Field(default=False, description="是否已确认")
    conversation_truncate_index: Optional[int] = Field(default=None, description="对话截断索引")


def mark_as_save_record(
    state: RouteMarkerInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> RouteMarkerOutput:
    """
    title: 标记为保存记录
    desc: 设置 route_after_save 为 save_record（使用指导/故障处理/评价等分支用）
    integrations: 
    """
    return RouteMarkerOutput(
        route_after_save="save_record",
        reply_content=state.reply_content,
        fallback_phase=state.fallback_phase,
        phone=state.phone,
        license_plate=state.license_plate,
        problem_summary=state.problem_summary,
        user_supplement=state.user_supplement,
        entry_problem=state.entry_problem,
        case_confirmed=state.case_confirmed,
        conversation_truncate_index=state.conversation_truncate_index
    )


def mark_as_cond_fallback(
    state: RouteMarkerInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> RouteMarkerOutput:
    """
    title: 标记为兜底流程判断
    desc: 设置 route_after_save 为 cond_fallback（兜底流程分支用）
    integrations: 
    """
    return RouteMarkerOutput(
        route_after_save="cond_fallback",
        reply_content=state.reply_content,
        fallback_phase=state.fallback_phase,
        phone=state.phone,
        license_plate=state.license_plate,
        problem_summary=state.problem_summary,
        user_supplement=state.user_supplement,
        entry_problem=state.entry_problem,
        case_confirmed=state.case_confirmed,
        conversation_truncate_index=state.conversation_truncate_index
    )
