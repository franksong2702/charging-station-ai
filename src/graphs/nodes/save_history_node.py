"""保存对话历史节点 - 用于多轮对话上下文"""
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from postgrest.exceptions import APIError

from graphs.state import SaveHistoryInput, SaveHistoryOutput
from storage.database.supabase_client import get_supabase_client


def save_history_node(
    state: SaveHistoryInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> SaveHistoryOutput:
    """
    title: 保存对话历史
    desc: 将当前对话保存到数据库，用于后续多轮对话上下文
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
        
        # 插入对话记录
        client.table("conversation_history").insert({
            "user_id": state.user_id,
            "user_message": state.user_message,
            "reply_content": state.reply_content,
            "intent": state.intent if state.intent else None
        }).execute()
        
        return SaveHistoryOutput(saved=True)
        
    except APIError as e:
        # 保存失败不影响主流程，记录错误但返回成功
        return SaveHistoryOutput(saved=False)
    except Exception as e:
        # 其他异常也不影响主流程
        return SaveHistoryOutput(saved=False)
