"""
充电桩智能客服工作流主图编排
支持评价机制，支持多轮对话，支持兜底流程和工单创建
"""
from langgraph.graph import StateGraph, END

from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
    IntentRecognitionInput,
    KnowledgeQAInput,
    FeedbackInput,
    InfoCollectionInput,
    EmailSendingInput,
    LoadHistoryInput,
    SaveHistoryInput,
    SaveRecordInput,
    DissatisfiedInput,
    SatisfiedInput,
    FallbackInput,
    CreateCaseInput,
    ClearFallbackStateInput,
    IntentRouteCheck,
    CaseConfirmedCheck
)

from graphs.nodes.intent_recognition_node import intent_recognition_node
from graphs.nodes.knowledge_qa_node import knowledge_qa_node
from graphs.nodes.feedback_node import feedback_node
from graphs.nodes.info_collection_node import info_collection_node
from graphs.nodes.email_sending_node import email_sending_node
from graphs.nodes.load_history_node import load_history_node
from graphs.nodes.save_history_node import save_history_node
from graphs.nodes.save_record_node import save_record_node
from graphs.nodes.dissatisfied_node import dissatisfied_node
from graphs.nodes.satisfied_node import satisfied_node
from graphs.nodes.fallback_node import fallback_node
from graphs.nodes.create_case_node import create_case_node
from graphs.nodes.clear_fallback_state_node import clear_fallback_state_node


# ==================== 条件判断函数 ====================

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


def cond_fallback(state: CaseConfirmedCheck) -> str:
    """
    title: 工单确认判断
    desc: 判断用户是否已确认问题总结，决定是否创建工单
    """
    if state.case_confirmed:
        return "创建工单"
    else:
        return "继续兜底"


# ==================== 主图编排 ====================

# 创建状态图
builder = StateGraph(
    GlobalState,
    input_schema=GraphInput,
    output_schema=GraphOutput
)

# ==================== 添加节点 ====================

# 加载对话历史
builder.add_node(
    "load_history",
    load_history_node,
    metadata={"type": "task"}
)

# 意图识别
builder.add_node(
    "intent_recognition",
    intent_recognition_node,
    metadata={
        "type": "agent",
        "llm_cfg": "config/intent_recognition_llm_cfg.json"
    }
)

# 知识库问答
builder.add_node(
    "knowledge_qa",
    knowledge_qa_node,
    metadata={
        "type": "agent",
        "llm_cfg": "config/knowledge_qa_llm_cfg.json"
    }
)

# 评价反馈处理
builder.add_node(
    "feedback",
    feedback_node,
    metadata={"type": "task"}
)

# 投诉信息收集（保留，用于投诉兜底场景）
builder.add_node(
    "info_collection",
    info_collection_node,
    metadata={
        "type": "agent",
        "llm_cfg": "config/info_collection_llm_cfg.json"
    }
)

# 邮件发送
builder.add_node(
    "email_sending",
    email_sending_node,
    metadata={"type": "task"}
)

# 保存对话历史
builder.add_node(
    "save_history",
    save_history_node,
    metadata={"type": "task"}
)

# 保存对话记录
builder.add_node(
    "save_record",
    save_record_node,
    metadata={"type": "task"}
)

# 轻度不满处理
builder.add_node(
    "dissatisfied",
    dissatisfied_node,
    metadata={"type": "task"}
)

# 满意处理
builder.add_node(
    "satisfied",
    satisfied_node,
    metadata={"type": "task"}
)

# 兜底流程
builder.add_node(
    "fallback",
    fallback_node,
    metadata={"type": "task"}
)

# 创建工单
builder.add_node(
    "create_case",
    create_case_node,
    metadata={"type": "task"}
)

# 清除兜底状态
builder.add_node(
    "clear_fallback_state",
    clear_fallback_state_node,
    metadata={"type": "task"}
)

# ==================== 设置入口点 ====================

builder.set_entry_point("load_history")

# ==================== 添加边 ====================

# 加载历史 → 意图识别（去掉 input_process 和语音处理）
builder.add_edge("load_history", "intent_recognition")

# 意图路由
builder.add_conditional_edges(
    source="intent_recognition",
    path=cond_intent_recognition,
    path_map={
        "使用指导": "knowledge_qa",
        "故障处理": "knowledge_qa",
        "兜底流程": "fallback",
        "不满意": "dissatisfied",
        "满意": "satisfied",
        "评价反馈": "feedback",
        "退出兜底": "clear_fallback_state"
    }
)

# 知识库问答 → 保存历史 → 保存记录 → 结束
builder.add_edge("knowledge_qa", "save_history")
builder.add_edge("save_history", "save_record")
builder.add_edge("save_record", END)

# 评价反馈 → 保存记录 → 结束
builder.add_edge("feedback", "save_record")

# 轻度不满 → 保存记录 → 结束
builder.add_edge("dissatisfied", "save_record")

# 满意 → 保存记录 → 结束
builder.add_edge("satisfied", "save_record")

# 兜底流程判断
builder.add_conditional_edges(
    source="fallback",
    path=cond_fallback,
    path_map={
        "创建工单": "create_case",
        "继续兜底": "save_history"
    }
)

# 创建工单 → 邮件发送 → 结束
builder.add_edge("create_case", "email_sending")
builder.add_edge("email_sending", END)

# 退出兜底 → 清除状态 → 知识库问答
builder.add_edge("clear_fallback_state", "knowledge_qa")

# 投诉兜底流程（保留旧流程兼容）
builder.add_edge("info_collection", "email_sending")

# ==================== 编译图 ====================

main_graph = builder.compile()
