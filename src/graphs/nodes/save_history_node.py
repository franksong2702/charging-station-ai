"""
保存对话历史节点 - 用于多轮对话上下文和兜底流程状态
"""
import logging
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from postgrest.exceptions import APIError

from graphs.state import SaveHistoryInput, SaveHistoryOutput
from storage.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def save_history_node(
    state: SaveHistoryInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> SaveHistoryOutput:
    """
    title: 保存对话历史
    desc: 将当前对话和兜底流程状态保存到数据库
    integrations: Supabase
    """
    # 如果没有 user_id，跳过保存
    if not state.user_id:
        return SaveHistoryOutput(saved=True)
    
    # 如果消息为空，跳过保存
    if not state.user_message or not state.reply_content:
        return SaveHistoryOutput(saved=True)
    
    try:
        client = get_supabase_client()
        
        # 构建插入数据
        insert_data = {
            "user_id": state.user_id,
            "user_message": state.user_message,
            "reply_content": state.reply_content,
            "intent": state.intent if state.intent else None
        }
        
        # 如果有兜底流程状态，也保存进去
        # 注意：如果 fallback_phase = "done"，表示兜底已完成，不保存兜底状态
        # 这样下次用户来对话时就是新会话
        if state.fallback_phase and state.fallback_phase != "done":
            insert_data["fallback_phase"] = state.fallback_phase
            if state.phone:
                insert_data["phone"] = state.phone
            if state.license_plate:
                insert_data["license_plate"] = state.license_plate
            if state.problem_summary:
                insert_data["problem_summary"] = state.problem_summary
            if state.entry_problem:
                insert_data["entry_problem"] = state.entry_problem
        
        # 插入对话记录
        client.table("conversation_history").insert(insert_data).execute()
        
        logger.info(f"保存对话历史成功 - user_id: {state.user_id}, fallback_phase: {state.fallback_phase}")
        return SaveHistoryOutput(saved=True)
        
    except APIError as e:
        # 保存失败不影响主流程，记录错误
        logger.error(f"保存对话历史失败 - APIError: {e}, 详情: {e.message if hasattr(e, 'message') else 'N/A'}, 数据: {insert_data}")
        return SaveHistoryOutput(saved=False)
    except Exception as e:
        # 其他异常也不影响主流程
        logger.error(f"保存对话历史失败 - Exception: {type(e).__name__}: {e}")
        return SaveHistoryOutput(saved=False)
