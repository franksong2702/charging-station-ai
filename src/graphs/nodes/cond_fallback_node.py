"""
工单确认判断条件节点 - 判断用户是否已确认问题总结
"""
from typing import Any
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import CaseConfirmedCheck
from pydantic import BaseModel, Field


class CondFallbackOutput(BaseModel):
    """条件节点输出（用于画布兼容性）"""
    route: str = Field(..., description="路由结果")


def cond_fallback(
    state: CaseConfirmedCheck,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> CondFallbackOutput:
    """
    title: 工单确认判断
    desc: 判断用户是否已确认问题总结，决定是否创建工单
    integrations:
    """
    if state.case_confirmed:
        return CondFallbackOutput(route="创建工单")
    else:
        return CondFallbackOutput(route="继续兜底")


def cond_fallback_path(state: CaseConfirmedCheck) -> str:
    """
    用于 add_conditional_edges 的路径函数（返回字符串）
    """
    if state.case_confirmed:
        return "创建工单"
    else:
        return "继续兜底"


# ==================== 清除兜底状态后的路由判断 ====================

class ClearFallbackStateRouteCheck(BaseModel):
    """清除兜底状态后的路由检查输入"""
    user_message: str = Field(default="", description="用户消息")
    case_confirmed: bool = Field(default=False, description="是否已确认工单")


class ClearFallbackRouteOutput(BaseModel):
    """清除兜底状态后的路由输出"""
    route: str = Field(..., description="路由结果")


def cond_clear_fallback_state_route(
    state: ClearFallbackStateRouteCheck,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> ClearFallbackRouteOutput:
    """
    title: 清除兜底状态后路由判断
    desc: 判断清除兜底状态后应该结束还是继续处理用户消息
    """
    # 如果是工单确认后触发的清除（case_confirmed=True），则结束
    if state.case_confirmed:
        return ClearFallbackRouteOutput(route="end")
    # 否则是用户退出兜底，继续处理用户消息
    else:
        return ClearFallbackRouteOutput(route="query_rewrite")


def cond_clear_fallback_state_route_path(state: ClearFallbackStateRouteCheck) -> str:
    """
    用于 add_conditional_edges 的路径函数（返回字符串）
    """
    if state.case_confirmed:
        return "end"
    else:
        return "query_rewrite"
