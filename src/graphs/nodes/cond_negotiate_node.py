"""
协商处理条件节点 - 判断用户是否接受方案
"""
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import NegotiateRouteCheck, NegotiateInput, NegotiateOutput


def cond_negotiate_route_path(state: NegotiateRouteCheck) -> str:
    """
    用于 add_conditional_edges 的路径函数（返回字符串）
    协商后路由判断：
    - 用户接受方案 → 结束
    - 用户拒绝方案 → 进入兜底
    - 用户继续追问 → 继续协商
    """
    user_message = state.user_message.lower()
    
    # 接受信号
    accept_keywords = ["好的", "可以", "行", "试试", "谢谢", "没问题"]
    for kw in accept_keywords:
        if kw in user_message:
            return "end"
    
    # 拒绝信号
    reject_keywords = ["不行", "不可以", "不接受", "必须", "一定要", "马上"]
    for kw in reject_keywords:
        if kw in user_message:
            return "fallback"
    
    # 默认继续协商
    return "negotiate"


def cond_negotiate(
    state: NegotiateInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> NegotiateOutput:
    """
    title: 协商处理条件判断
    desc: 判断用户是否接受协商方案，决定后续流程
    integrations: 
    """
    # 这个节点暂时不做实际处理，主要是用 cond_negotiate_route_path 做路由
    # 后续如果需要可以在这里添加逻辑
    return NegotiateOutput(
        reply_content="",
        negotiate_phase="asking",
        problem_understanding=""
    )
