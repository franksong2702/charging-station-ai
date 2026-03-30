"""
加载对话历史节点 - 用于多轮对话上下文和兜底流程状态
"""
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
    desc: 根据用户ID从数据库加载历史对话记录和兜底流程状态
    integrations: Supabase
    """
    # 如果没有 user_id，返回空历史
    if not state.user_id:
        return LoadHistoryOutput(
            conversation_history=[],
            fallback_phase="",
            phone="",
            license_plate="",
            problem_summary=""
        )
    
    try:
        client = get_supabase_client()
        
        # 查询最近 N 轮对话历史
        # 每轮对话包含用户消息和AI回复，所以需要 2 * MAX_HISTORY_ROUNDS 条记录
        limit = MAX_HISTORY_ROUNDS * 2
        
        response = client.table("conversation_history") \
            .select("user_message, reply_content, created_at, fallback_phase, phone, license_plate, problem_summary") \
            .eq("user_id", state.user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        # 检查响应数据
        if response is None or not hasattr(response, 'data') or response.data is None:
            return LoadHistoryOutput(
                conversation_history=[],
                fallback_phase="",
                phone="",
                license_plate="",
                problem_summary=""
            )
        
        data = response.data
        if not isinstance(data, list) or len(data) == 0:
            # 数据库无记录，使用 GraphInput 中的兜底流程状态
            return LoadHistoryOutput(
                conversation_history=[],
                fallback_phase=state.fallback_phase,
                phone=state.phone,
                license_plate=state.license_plate,
                problem_summary=state.problem_summary
            )
        
        # 转换为对话历史格式，并按时间正序排列
        history: List[Dict[str, str]] = []
        
        # 从最新的记录中获取兜底流程状态
        latest_record = data[0] if data else {}
        fallback_phase = ""
        phone = ""
        license_plate = ""
        problem_summary = ""
        
        if isinstance(latest_record, dict):
            fallback_phase = str(latest_record.get("fallback_phase") or "")
            phone = str(latest_record.get("phone") or "")
            license_plate = str(latest_record.get("license_plate") or "")
            problem_summary = str(latest_record.get("problem_summary") or "")
        
        # 如果 GraphInput 中传入了兜底流程状态，优先使用（支持云函数传递状态）
        if state.fallback_phase:
            fallback_phase = state.fallback_phase
        if state.phone:
            phone = state.phone
        if state.license_plate:
            license_plate = state.license_plate
        if state.problem_summary:
            problem_summary = state.problem_summary
        
        # 构建对话历史
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
        
        return LoadHistoryOutput(
            conversation_history=history,
            fallback_phase=fallback_phase,
            phone=phone,
            license_plate=license_plate,
            problem_summary=problem_summary
        )
        
    except APIError as e:
        # 查询失败不影响主流程，返回空历史
        return LoadHistoryOutput(
            conversation_history=[],
            fallback_phase="",
            phone="",
            license_plate="",
            problem_summary=""
        )
    except Exception as e:
        # 其他异常也不影响主流程
        return LoadHistoryOutput(
            conversation_history=[],
            fallback_phase="",
            phone="",
            license_plate="",
            problem_summary=""
        )
