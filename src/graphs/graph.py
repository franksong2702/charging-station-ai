"""
充电桩智能客服工作流主图编排
支持评价机制，支持多轮对话，支持兜底流程和工单创建
支持分层客服架构（协商处理层）

核心原则：所有和用户的对话，不管是什么情况，都先保存对话历史！
路由方案：用 route_after_save 字段标记，save_history 之后统一路由
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
    CaseConfirmedCheck,
    NegotiateInput,
    NegotiateRouteCheck,
    AfterSaveRouteCheck
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
from graphs.nodes.cond_fallback_node import cond_fallback, cond_fallback_path
from graphs.nodes.negotiate_node import negotiate_node
from graphs.nodes.cond_negotiate_node import cond_negotiate, cond_negotiate_route_path
from graphs.nodes.cond_after_save_node import cond_after_save, cond_after_save_route_path
from graphs.nodes.route_marker_nodes import (
    mark_as_save_record,
    mark_as_cond_fallback,
    mark_as_cond_negotiate
)


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

# 协商处理条件节点已删除，简化路由

# save_history 之后的统一条件路由节点
builder.add_node(
    "cond_after_save",
    cond_after_save,
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

# 协商处理
builder.add_node(
    "negotiate",
    negotiate_node,
    metadata={
        "type": "agent",
        "llm_cfg": "config/negotiate_llm_cfg.json"
    }
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

# ==================== 路由标记节点（用于设置 route_after_save） ====================
builder.add_node(
    "mark_as_save_record",
    mark_as_save_record,
    metadata={"type": "task"}
)

builder.add_node(
    "mark_as_cond_fallback",
    mark_as_cond_fallback,
    metadata={"type": "task"}
)

builder.add_node(
    "mark_as_cond_negotiate",
    mark_as_cond_negotiate,
    metadata={"type": "task"}
)

# ==================== 设置入口点 ====================

builder.set_entry_point("load_history")

# ==================== 添加边（新的路由方案：用 route_after_save 标记） ====================

# 加载历史 → 意图识别
builder.add_edge("load_history", "intent_recognition")

# 意图路由 → 各个处理节点
builder.add_conditional_edges(
    source="intent_recognition",
    path=cond_intent_recognition_path,
    path_map={
        "使用指导": "query_rewrite",
        "故障处理": "query_rewrite",
        "协商处理": "negotiate",
        "兜底流程": "fallback",
        "不满意": "dissatisfied",
        "满意": "satisfied",
        "评价反馈": "feedback",
        "退出兜底": "clear_fallback_state"
    }
)

# ==================== 分支 1：使用指导/故障处理 → 改写 → 问答 → 标记 → 保存历史 ====================
builder.add_edge("query_rewrite", "knowledge_qa")
builder.add_edge("knowledge_qa", "mark_as_save_record")
builder.add_edge("mark_as_save_record", "save_history")

# ==================== 分支 2：评价反馈/轻度不满/满意 → 处理 → 标记 → 保存历史 ====================
builder.add_edge("feedback", "mark_as_save_record")
builder.add_edge("dissatisfied", "mark_as_save_record")
builder.add_edge("satisfied", "mark_as_save_record")
builder.add_edge("mark_as_save_record", "save_history")

# ==================== 分支 3：兜底流程 → 处理 → 标记 → 保存历史 ====================
builder.add_edge("fallback", "mark_as_cond_fallback")
builder.add_edge("mark_as_cond_fallback", "save_history")

# ==================== 分支 4：协商处理 → 处理 → 标记 → 保存历史 ====================
builder.add_edge("negotiate", "mark_as_cond_negotiate")
builder.add_edge("mark_as_cond_negotiate", "save_history")

# ==================== 核心：save_history 之后的统一条件路由 ====================
builder.add_conditional_edges(
    source="save_history",
    path=cond_after_save_route_path,
    path_map={
        "save_record": "save_record",
        "cond_fallback": "cond_fallback",
        "cond_negotiate": "save_record"  # 协商处理后统一走 save_record
    }
)

# ==================== save_record 分支 → 结束 ====================
builder.add_edge("save_record", END)

# ==================== cond_fallback 分支 → 原有的兜底路由 ====================
builder.add_conditional_edges(
    source="cond_fallback",
    path=cond_fallback_path,
    path_map={
        "创建工单": "create_case",
        "继续兜底": END
    }
)

# 创建工单 → 邮件发送 → 清除兜底状态 → 结束
builder.add_edge("create_case", "email_sending")
builder.add_edge("email_sending", "clear_fallback_state")
builder.add_edge("clear_fallback_state", END)

# ==================== cond_negotiate 分支已删除，简化路由 ====================
# 协商处理后直接保存历史，后续根据用户下一条消息判断

# 退出兜底 → 直接结束
builder.add_edge("clear_fallback_state", END)

# ==================== 编译图 ====================

main_graph = builder.compile()
