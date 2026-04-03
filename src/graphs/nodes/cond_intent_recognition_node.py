"""
意图路由条件节点 - 根据意图识别结果决定后续处理流程
"""
from graphs.state import IntentRouteCheck


def cond_intent_recognition(state: IntentRouteCheck) -> str:
    """
    title: 意图路由
    desc: 根据意图识别结果，决定后续处理流程
    """
    intent = state.intent
    
    if intent == "usage_guidance":
        return "使用指导"
    elif intent == "fault_handling":
        return "故障处理"
    elif intent == "complaint":
        return "兜底流程"
    elif intent == "fallback":
        return "兜底流程"
    elif intent == "cancel_fallback":
        return "退出兜底"
    elif intent == "exit_fallback":
        return "退出兜底"
    elif intent == "dissatisfied":
        return "不满意"
    elif intent == "satisfied":
        return "满意"
    elif intent == "feedback_good":
        return "评价反馈"
    elif intent == "feedback_bad":
        return "评价反馈"
    else:
        return "使用指导"
