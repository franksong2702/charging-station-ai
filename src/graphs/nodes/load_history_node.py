"""加载对话历史节点 - 用于多轮对话上下文"""
from typing import Dict, Any, List, Optional, cast
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from postgrest.exceptions import APIError

from graphs.state import LoadHistoryInput, LoadHistoryOutput
from storage.database.supabase_client import get_supabase_client


# 最大保留的对话轮数（每轮包含用户消息和AI回复）
MAX_HISTORY_ROUNDS = 10


def load_history_node(
    state: LoadHistoryInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> LoadHistoryOutput:
    """
    title: 加载对话历史
    desc: 根据用户ID从数据库加载历史对话记录，用于多轮对话上下文
    integrations: Supabase
    """
    # 如果没有 user_id，返回空历史
    if not state.user_id:
        return LoadHistoryOutput(conversation_history=[])
    
    try:
        client = get_supabase_client()
        
        # 查询最近 N 轮对话历史
        # 每轮对话包含用户消息和AI回复，所以需要 2 * MAX_HISTORY_ROUNDS 条记录
        limit = MAX_HISTORY_ROUNDS * 2
        
        response = client.table("conversation_history") \
            .select("user_message, reply_content, created_at") \
            .eq("user_id", state.user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        # 检查响应数据
        if response is None or not hasattr(response, 'data') or response.data is None:
            return LoadHistoryOutput(conversation_history=[])
        
        data = response.data
        if not isinstance(data, list) or len(data) == 0:
            return LoadHistoryOutput(conversation_history=[])
        
        # 转换为对话历史格式，并按时间正序排列
        history: List[Dict[str, str]] = []
        for record in reversed(data):
            if not isinstance(record, dict):
                continue
            user_msg = record.get("user_message", "")
            reply = record.get("reply_content", "")
            if user_msg:
                history.append({
                    "role": "user",
                    "content": str(user_msg)
                })
            if reply:
                history.append({
                    "role": "assistant",
                    "content": str(reply)
                })
        
        return LoadHistoryOutput(conversation_history=history)
        
    except APIError as e:
        # 查询失败不影响主流程，返回空历史
        return LoadHistoryOutput(conversation_history=[])
    except Exception as e:
        # 其他异常也不影响主流程
        return LoadHistoryOutput(conversation_history=[])
