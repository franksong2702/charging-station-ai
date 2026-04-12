"""
save_history 之后的统一条件路由节点 - 根据 route_after_save 字段判断后续流程
"""
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from pydantic import BaseModel, Field
from typing import Literal


class AfterSaveRouteCheck(BaseModel):
    """save_history 之后路由检查的输入"""
    route_after_save: str = Field(default="", description="路由标记：save_record/cond_fallback/cond_negotiate")
    # 兜底流程相关
    case_confirmed: bool = Field(default=False, description="用户是否已确认问题总结")
    # 协商处理相关
    user_message: str = Field(default="", description="用户消息（用于协商处理路由判断）")
    route_to_fallback: bool = Field(default=False, description="是否需要路由到兜底流程（协商失败时）")


class AfterSaveRouteOutput(BaseModel):
    """条件节点输出（用于画布兼容性）"""
    route: str = Field(..., description="路由结果")


def cond_after_save_route_path(state: AfterSaveRouteCheck) -> str:
    """
    用于 add_conditional_edges 的路径函数（返回字符串）
    save_history 之后的统一路由判断
    """
    # 优先检查 route_to_fallback（协商失败时升级到兜底）
    if getattr(state, 'route_to_fallback', False):
        return "cond_fallback"
    
    route_marker = state.route_after_save
    
    if route_marker == "save_record":
        # 使用指导/故障处理/评价反馈/满意/不满意 → 去 save_record
        return "save_record"
    elif route_marker == "cond_fallback":
        # 兜底流程 → 去 cond_fallback 判断
        return "cond_fallback"
    elif route_marker == "cond_negotiate":
        # 协商处理 → 去 cond_negotiate 判断
        return "cond_negotiate"
    else:
        # 默认去 save_record
        return "save_record"


def cond_after_save(
    state: AfterSaveRouteCheck,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> AfterSaveRouteOutput:
    """
    title: save_history 后统一路由
    desc: 根据 route_after_save 字段判断后续流程
    integrations: 
    """
    route = cond_after_save_route_path(state)
    return AfterSaveRouteOutput(route=route)
