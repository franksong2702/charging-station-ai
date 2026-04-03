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
