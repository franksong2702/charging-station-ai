"""
条件判断节点 - 工单确认判断
"""
from graphs.state import CaseConfirmedCheck


def cond_fallback(state: CaseConfirmedCheck) -> str:
    """
    title: 工单确认判断
    desc: 判断用户是否已确认问题总结，决定是否创建工单
    """
    if state.case_confirmed:
        return "创建工单"
    else:
        return "继续兜底"
