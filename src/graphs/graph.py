"""
充电桩智能客服工作流主图编排
支持文字和语音输入，支持评价机制和对话记录保存
"""
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
    InputProcessInput,
    ASRInput,
    IntentRecognitionInput,
    KnowledgeQAInput,
    FeedbackInput,
    SaveRecordInput,
    InfoCollectionInput,
    EmailSendingInput
)

from graphs.nodes.input_process_node import input_process_node
from graphs.nodes.asr_node import asr_node
from graphs.nodes.intent_recognition_node import intent_recognition_node
from graphs.nodes.knowledge_qa_node import knowledge_qa_node
from graphs.nodes.feedback_node import feedback_node
from graphs.nodes.save_record_node import save_record_node
from graphs.nodes.info_collection_node import info_collection_node
from graphs.nodes.email_sending_node import email_sending_node


# ==================== 条件判断函数 ====================

def route_by_voice_input(state: GlobalState) -> str:
    """
    title: 语音输入判断
    desc: 判断是否有语音输入，决定是否需要 ASR 处理
    """
    # 如果有语音 URL，走 ASR 处理
    if state.voice_url and state.voice_url.strip():
        return "语音处理"
    else:
        return "直接处理文字"


def route_by_intent(state: GlobalState) -> str:
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
        return "投诉兜底"
    elif intent == "feedback_good":
        return "评价反馈"
    elif intent == "feedback_bad":
        return "评价反馈"
    else:
        # 默认走知识库问答
        return "使用指导"


# ==================== 主图编排 ====================

# 创建状态图
builder = StateGraph(
    GlobalState,
    input_schema=GraphInput,
    output_schema=GraphOutput
)

# 添加节点
builder.add_node(
    "input_process",
    input_process_node
)

builder.add_node(
    "asr",
    asr_node,
    metadata={
        "type": "task"
    }
)

builder.add_node(
    "intent_recognition",
    intent_recognition_node,
    metadata={
        "type": "agent",
        "llm_cfg": "config/intent_recognition_llm_cfg.json"
    }
)

builder.add_node(
    "knowledge_qa",
    knowledge_qa_node,
    metadata={
        "type": "agent",
        "llm_cfg": "config/knowledge_qa_llm_cfg.json"
    }
)

builder.add_node(
    "feedback",
    feedback_node,
    metadata={
        "type": "task"
    }
)

builder.add_node(
    "save_record",
    save_record_node,
    metadata={
        "type": "task"
    }
)

builder.add_node(
    "info_collection",
    info_collection_node,
    metadata={
        "type": "agent",
        "llm_cfg": "config/info_collection_llm_cfg.json"
    }
)

builder.add_node(
    "email_sending",
    email_sending_node,
    metadata={
        "type": "task"
    }
)

# 设置入口点
builder.set_entry_point("input_process")

# 添加条件分支：判断是否有语音输入
builder.add_conditional_edges(
    source="input_process",
    path=route_by_voice_input,
    path_map={
        "语音处理": "asr",
        "直接处理文字": "intent_recognition"
    }
)

# ASR 处理后，进入意图识别
builder.add_edge("asr", "intent_recognition")

# 添加意图分支
builder.add_conditional_edges(
    source="intent_recognition",
    path=route_by_intent,
    path_map={
        "使用指导": "knowledge_qa",
        "故障处理": "knowledge_qa",
        "投诉兜底": "info_collection",
        "评价反馈": "feedback"
    }
)

# 知识库问答后直接结束（暂时移除保存记录功能）
builder.add_edge("knowledge_qa", END)

# 评价反馈后直接结束（暂时移除保存记录功能）
builder.add_edge("feedback", END)

# 投诉处理流程
builder.add_edge("info_collection", "email_sending")
builder.add_edge("email_sending", END)

# 编译图
main_graph = builder.compile()
