"""
对话记录保存节点 - 将对话记录保存到Supabase数据库
"""
import json
import logging
from typing import List, Dict, Any

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from postgrest.exceptions import APIError

from graphs.state import SaveRecordInput, SaveRecordOutput
from storage.database.supabase_client import get_supabase_client

# 配置日志
logger = logging.getLogger(__name__)


def _extract_context_from_history(
    conversation_history: List[Dict[str, str]]
) -> Dict[str, str]:
    """
    从对话历史中提取原始问题和回答（用户评价之前的那一对问答）
    
    Args:
        conversation_history: 对话历史列表，格式为 [{"role": "user/assistant", "content": "..."}]
    
    Returns:
        包含原始问题和回答的字典
    """
    context = {
        "original_question": "",
        "original_answer": ""
    }
    
    if not conversation_history or len(conversation_history) < 2:
        return context
    
    # 对话历史示例（评价场景）:
    # [0] user: 特斯拉怎么充电？        ← 这是原始问题
    # [1] assistant: 您好，特斯拉...    ← 这是原始回答
    # [2] user: 好的，谢谢！           ← 触发评价的消息
    # [3] assistant: 不客气😊...评价提示 ← 带评价提示的回复
    
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
    desc: 将对话记录保存到数据库，用于后续分析
    integrations: Supabase
    """
    ctx = runtime.context
    
    # 构建记录对象
    knowledge_matched = len(state.knowledge_chunks) > 0
    knowledge_chunks_summary = [
        {"content": chunk.get("content", "")[:100], "score": chunk.get("score", 0)}
        for chunk in state.knowledge_chunks[:3]  # 只保存前3条
    ]
    
    # 如果是评价反馈，提取原始问题和回答
    original_question = None
    original_answer = None
    
    if state.feedback_type in ["good", "bad"]:
        context = _extract_context_from_history(state.conversation_history)
        original_question = context.get("original_question") or None
        original_answer = context.get("original_answer") or None
        
        if original_question:
            logger.info(f"评价记录 - 原始问题: {original_question[:50]}...")
            logger.info(f"评价记录 - 原始回答: {(original_answer or '')[:50]}...")
    
    try:
        client = get_supabase_client()
        
        # 构建插入数据
        record_data = {
            "user_id": state.user_id if state.user_id else None,
            "user_message": state.user_message,
            "reply_content": state.reply_content,
            "intent": state.intent if state.intent else None,
            "feedback_type": state.feedback_type if state.feedback_type else None,
            "knowledge_matched": knowledge_matched,
            "knowledge_chunks": knowledge_chunks_summary if knowledge_chunks_summary else None
        }
        
        # 如果是评价反馈，把原始问题和回答保存到 knowledge_chunks 字段
        # （评价时 knowledge_chunks 为空，可以复用这个字段）
        if state.feedback_type in ["good", "bad"]:
            if original_question or original_answer:
                # 复用 knowledge_chunks 字段保存上下文
                record_data["knowledge_chunks"] = [{
                    "type": "evaluation_context",
                    "original_question": original_question,
                    "original_answer": original_answer
                }]
        
        # 插入对话记录
        client.table("dialog_records").insert(record_data).execute()
        
        logger.info(f"对话记录已保存到数据库")
        return SaveRecordOutput(saved=True)
        
    except APIError as e:
        logger.error(f"保存记录到数据库失败: {e.message}")
        return SaveRecordOutput(saved=False)
    except Exception as e:
        logger.error(f"保存记录失败: {str(e)}")
        return SaveRecordOutput(saved=False)
