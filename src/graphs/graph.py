"""
充电桩智能客服工作流主图编排
支持评价机制，支持多轮对话，支持兜底流程和工单创建

核心原则：所有和用户的对话，不管是什么情况，都先保存对话历史！
"""
from langgraph.graph import StateGraph, END

from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
    IntentRecognitionInput,
    QueryRewriteInput,
    KnowledgeQAInput,
    FeedbackInput,
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
from graphs.nodes.query_rewrite_node import query_rewrite_node
from graphs.nodes.knowledge_qa_node import knowledge_qa_node
from graphs.nodes.feedback_node import feedback_node
from graphs.nodes.email_sending_node import email_sending_node
from graphs.nodes.load_history_node import load_history_node
from graphs.nodes.save_history_node import save_history_node
from graphs.nodes.save_record_node import save_record_node
from graphs.nodes.dissatisfied_node import dissatisfied_node
from graphs.nodes.satisfied_node import satisfied_node
from graphs.nodes.fallback_node import fallback_node
from graphs.nodes.create_case_node import create_case_node
from graphs.nodes.clear_fallback_state_node import clear_fallback_state_node
from graphs.nodes.cond_intent_recognition_node import cond_intent_recognition, cond_intent_recognition_path
from graphs.nodes.cond_fallback_node import cond_fallback, cond_fallback_path, cond_clear_fallback_state_route, cond_clear_fallback_state_route_path


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

# 意图路由条件节点
builder.add_node(
    "cond_intent_recognition",
    cond_intent_recognition,
    metadata={"type": "condition"}
)

# 工单确认条件节点
builder.add_node(
    "cond_fallback",
    cond_fallback,
    metadata={"type": "condition"}
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

# 查询改写
builder.add_node(
    "query_rewrite",
    query_rewrite_node,
    metadata={
        "type": "agent",
        "llm_cfg": "config/query_rewrite_llm_cfg.json"
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

# 邮件发送
builder.add_node(
    "email_sending",
    email_sending_node,
    metadata={"type": "task"}
)

# ==================== 核心原则：所有对话必经此节点！ ====================
# 保存对话历史（不管是什么情况，所有回复用户前先保存对话！）
builder.add_node(
    "save_history",
    save_history_node,
    metadata={"type": "task"}
)

# 保存对话记录（只在评价/不满意等需要记录时走）
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

# ==================== 添加边（核心修改：所有分支先保存对话历史） ====================

# 加载历史 → 意图识别
builder.add_edge("load_history", "intent_recognition")

# 意图路由 → 各个处理节点
builder.add_conditional_edges(
    source="intent_recognition",
    path=cond_intent_recognition_path,
    path_map={
        "使用指导": "query_rewrite",
        "故障处理": "query_rewrite",
        "兜底流程": "fallback",
        "不满意": "dissatisfied",
        "满意": "satisfied",
        "评价反馈": "feedback",
        "退出兜底": "clear_fallback_state"
    }
)

# ==================== 分支 1：使用指导/故障处理 → 改写 → 问答 → 保存历史 → 保存记录 → 结束 ====================
builder.add_edge("query_rewrite", "knowledge_qa")
builder.add_edge("knowledge_qa", "save_history")
builder.add_edge("save_history", "save_record")
builder.add_edge("save_record", END)

# ==================== 分支 2：评价反馈/轻度不满/满意 → 处理 → 保存历史 → 保存记录 → 结束 ====================
# 注意：这些分支都要走 save_history！不能直接跳 save_record！
builder.add_edge("feedback", "save_history")
builder.add_edge("dissatisfied", "save_history")
builder.add_edge("satisfied", "save_history")
# 统一从 save_history 到 save_record
builder.add_edge("save_history", "save_record")
builder.add_edge("save_record", END)

# ==================== 分支 3：兜底流程 → 处理 → 保存历史 → 判断后续 ====================
# 兜底流程处理后，先走 save_history 保存对话
builder.add_edge("fallback", "save_history")

# 保存历史后，再判断是创建工单还是结束（继续兜底就结束，下次再进来）
builder.add_conditional_edges(
    source="save_history",
    path=cond_fallback_path,
    path_map={
        "创建工单": "create_case",
        "继续兜底": END
    }
)

# 创建工单 → 邮件发送 → 清除兜底状态 → 结束
builder.add_edge("create_case", "email_sending")
builder.add_edge("email_sending", "clear_fallback_state")

# 清除兜底状态后直接结束（避免循环）
builder.add_edge("clear_fallback_state", END)

# ==================== 编译图 ====================

main_graph = builder.compile()
