"""
意图路由条件节点 - 根据意图识别结果决定后续处理流程（简化为两层分流）
"""
from typing import Any
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import IntentRouteCheck
from pydantic import BaseModel, Field


class CondIntentRecognitionOutput(BaseModel):
    """条件节点输出（用于画布兼容性）"""
    route: str = Field(..., description="路由结果")


def cond_intent_recognition(
    state: IntentRouteCheck, 
    config: RunnableConfig, 
    runtime: Runtime[Context]
) -> CondIntentRecognitionOutput:
    """
    title: 意图路由
    desc: 根据意图识别结果，决定后续处理流程（简化为两层分流）
    integrations: 
    """
    intent = state.intent
    route = ""
    
    if intent == "usage_guidance":
        route = "使用指导"
    elif intent == "fault_handling":
        route = "故障处理"
    elif intent == "fallback":
        route = "兜底流程"
    elif intent == "dissatisfied":
        route = "不满意"
    elif intent == "satisfied":
        route = "满意"
    elif intent == "feedback_good":
        route = "评价反馈"
    elif intent == "feedback_bad":
        route = "评价反馈"
    elif intent == "exit_fallback":
        route = "退出兜底"
    else:
        # 默认都兜底流程
        route = "兜底流程"
    
    return CondIntentRecognitionOutput(route=route)


def cond_intent_recognition_path(state: IntentRouteCheck) -> str:
    """
    用于 add_conditional_edges 的路径函数（返回字符串）
    简化为两层分流
    """
    intent = state.intent
    
    if intent == "usage_guidance":
        return "使用指导"
    elif intent == "fault_handling":
        return "故障处理"
    elif intent == "fallback":
        return "兜底流程"
    elif intent == "dissatisfied":
        return "不满意"
    elif intent == "satisfied":
        return "满意"
    elif intent == "feedback_good":
        return "评价反馈"
    elif intent == "feedback_bad":
        return "评价反馈"
    elif intent == "exit_fallback":
        return "退出兜底"
    else:
        # 默认都兜底流程
        return "兜底流程"
