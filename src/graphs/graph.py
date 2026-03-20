"""
充电桩智能客服工作流主图编排
"""
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
    IntentRecognitionInput,
    KnowledgeQAInput,
    InfoCollectionInput,
    EmailSendingInput
)

from graphs.nodes.intent_recognition_node import intent_recognition_node
from graphs.nodes.knowledge_qa_node import knowledge_qa_node
from graphs.nodes.info_collection_node import info_collection_node
from graphs.nodes.email_sending_node import email_sending_node


# ==================== 条件判断函数 ====================

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
builder.set_entry_point("intent_recognition")

# 添加条件分支
builder.add_conditional_edges(
    source="intent_recognition",
    path=route_by_intent,
    path_map={
        "使用指导": "knowledge_qa",
        "故障处理": "knowledge_qa",
        "投诉兜底": "info_collection"
    }
)

# 添加后续边
builder.add_edge("knowledge_qa", END)
builder.add_edge("info_collection", "email_sending")
builder.add_edge("email_sending", END)

# 编译图
main_graph = builder.compile()
