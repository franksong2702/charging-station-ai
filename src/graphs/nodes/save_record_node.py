"""
对话记录保存节点 - 保存有价值的对话记录到 PostgreSQL 数据库
只保存：评价反馈、不满意场景（用于知识库优化）
"""
import json
import logging
from typing import List, Dict, Any

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import SaveRecordInput, SaveRecordOutput
from storage.database.db import get_session
from storage.database.shared.model import DialogRecord

# 配置日志
logger = logging.getLogger(__name__)


def _extract_context_from_history(
    conversation_history: List[Dict[str, str]]
) -> Dict[str, str]:
    """
    从对话历史中提取原始问题和回答
    
    Args:
        conversation_history: 对话历史列表
    
    Returns:
        包含原始问题和回答的字典
    """
    context = {
        "original_question": "",
        "original_answer": ""
    }
    
    if not conversation_history or len(conversation_history) < 2:
        return context
    
    # 找到第一个 user 消息作为原始问题
    # 找到第一个 assistant 消息作为原始回答
    for msg in conversation_history:
        if msg.get("role") == "user" and msg.get("content") and not context["original_question"]:
            context["original_question"] = msg["content"]
        if msg.get("role") == "assistant" and msg.get("content") and not context["original_answer"]:
            # 移除评价提示部分，只保留回答内容
            content = msg["content"]
            if "───────────" in content:
                content = content.split("───────────")[0].strip()
            context["original_answer"] = content
        if context["original_question"] and context["original_answer"]:
            break
    
    return context


def save_record_node(
    state: SaveRecordInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> SaveRecordOutput:
    """
    title: 对话记录保存
    desc: 只保存有价值的记录（评价/不满意），用于知识库优化和服务改进
    integrations: PostgreSQL
    """
    ctx = runtime.context
    
    intent = state.intent or ""
    feedback_type = state.feedback_type or ""
    
    # ==================== 判断是否需要保存 ====================
    # 保存以下场景：
    # 1. 评价反馈（good/bad）
    # 2. 不满意场景（dissatisfied）
    # 3. 知识库缺失场景（knowledge_missed） - 用于后续知识库扩充
    # 
    # 不保存：
    # - 普通问答（usage_guidance, fault_handling）且知识库有内容
    # - 兜底场景（fallback, complaint）→ 由 case_records 表保存
    
    should_save = False
    record_type = ""
    
    if feedback_type in ["good", "bad"]:
        should_save = True
        record_type = "评价反馈"
    elif intent == "dissatisfied":
        should_save = True
        record_type = "不满意反馈"
    elif state.knowledge_missed:
        should_save = True
        record_type = "知识库缺失"
    
    if not should_save:
        logger.info(f"跳过保存 - 意图: {intent}, 不属于有价值记录")
        return SaveRecordOutput(saved=False)
    
    logger.info(f"保存记录 - 类型: {record_type}, 意图: {intent}")
    
    # ==================== 提取上下文信息 ====================
    original_question = None
    original_answer = None
    
    context = _extract_context_from_history(state.conversation_history)
    original_question = context.get("original_question") or None
    original_answer = context.get("original_answer") or None
    
    if original_question:
        logger.info(f"记录上下文 - 原始问题: {original_question[:50]}...")
    
    # ==================== 保存到数据库 ====================
    session = None
    try:
        session = get_session()
        
        # 构建插入数据
        record = DialogRecord(
            user_id=state.user_id if state.user_id else None,
            user_message=state.user_message,
            reply_content=state.reply_content,
            intent=intent,
            feedback_type=feedback_type if feedback_type else None,
            knowledge_matched=len(state.knowledge_chunks) > 0,
            record_type=record_type,
            knowledge_chunks=[{
                "type": "feedback_context",
                "original_question": original_question,
                "original_answer": original_answer,
                "dissatisfied_reason": state.user_message if intent == "dissatisfied" else None
            }]
        )
        
        # 插入对话记录
        session.add(record)
        session.commit()
        
        logger.info(f"对话记录已保存到数据库")
        return SaveRecordOutput(saved=True)
        
    except Exception as e:
        if session:
            session.rollback()
        logger.error(f"保存记录失败: {str(e)}")
        return SaveRecordOutput(saved=False)
    finally:
        if session:
            session.close()
