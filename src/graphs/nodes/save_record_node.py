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
    
    try:
        client = get_supabase_client()
        
        # 插入对话记录
        client.table("dialog_records").insert({
            "user_id": state.user_id if state.user_id else None,
            "user_message": state.user_message,
            "reply_content": state.reply_content,
            "intent": state.intent if state.intent else None,
            "feedback_type": state.feedback_type if state.feedback_type else None,
            "knowledge_matched": knowledge_matched,
            "knowledge_chunks": knowledge_chunks_summary if knowledge_chunks_summary else None
        }).execute()
        
        logger.info(f"对话记录已保存到数据库")
        return SaveRecordOutput(saved=True)
        
    except APIError as e:
        logger.error(f"保存记录到数据库失败: {e.message}")
        return SaveRecordOutput(saved=False)
    except Exception as e:
        logger.error(f"保存记录失败: {str(e)}")
        return SaveRecordOutput(saved=False)
