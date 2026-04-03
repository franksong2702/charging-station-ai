"""
加载对话历史节点 - 用于多轮对话上下文和兜底流程状态
"""
import logging
from typing import Dict, Any, List, Optional, cast
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import LoadHistoryInput, LoadHistoryOutput
from storage.database.db import get_session
from storage.database.shared.model import ConversationHistory

logger = logging.getLogger(__name__)


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
    integrations: PostgreSQL
    """
    # 如果没有 user_id，返回空历史，但保留 GraphInput 中的兜底流程状态
    if not state.user_id:
        return LoadHistoryOutput(
            conversation_history=[],
            fallback_phase=state.fallback_phase,  # 保留传入的状态
            phone=state.phone,
            license_plate=state.license_plate,
            problem_summary=state.problem_summary,
            entry_problem=state.entry_problem
        )
    
    try:
        session = get_session()
        
        # 查询最近 N 轮对话历史
        # 每轮对话包含用户消息和AI回复，所以需要 2 * MAX_HISTORY_ROUNDS 条记录
        limit = MAX_HISTORY_ROUNDS * 2
        
        records = session.query(ConversationHistory) \
            .filter(ConversationHistory.user_id == state.user_id) \
            .order_by(ConversationHistory.created_at.desc()) \
            .limit(limit) \
            .all()
        
        session.close()
        
        if not records:
            # 数据库无记录，使用 GraphInput 中的兜底流程状态
            return LoadHistoryOutput(
                conversation_history=[],
                fallback_phase=state.fallback_phase,
                phone=state.phone,
                license_plate=state.license_plate,
                problem_summary=state.problem_summary,
                entry_problem=state.entry_problem
            )
        
        # 转换为对话历史格式，并按时间正序排列
        history: List[Dict[str, str]] = []
        
        # 从最新的记录中获取兜底流程状态
        latest_record = records[0] if records else None
        fallback_phase = ""
        phone = ""
        license_plate = ""
        problem_summary = ""
        entry_problem = ""
        
        if latest_record:
            fallback_phase = str(latest_record.fallback_phase or "")
            phone = str(latest_record.phone or "")
            license_plate = str(latest_record.license_plate or "")
            problem_summary = str(latest_record.problem_summary or "")
            entry_problem = str(latest_record.entry_problem or "")
        
        # 如果 GraphInput 中传入了兜底流程状态，优先使用（支持云函数传递状态）
        if state.fallback_phase:
            fallback_phase = state.fallback_phase
        if state.phone:
            phone = state.phone
        if state.license_plate:
            license_plate = state.license_plate
        if state.problem_summary:
            problem_summary = state.problem_summary
        if state.entry_problem:
            entry_problem = state.entry_problem
        
        # 构建对话历史（按时间正序）
        for record in reversed(records):
            user_msg = record.user_message or ""
            reply = record.reply_content or ""
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
            problem_summary=problem_summary,
            entry_problem=entry_problem
        )
        
    except Exception as e:
        # 查询失败不影响主流程，记录错误并返回空历史
        logger.error(f"加载对话历史失败 - Exception: {type(e).__name__}: {e}")
        return LoadHistoryOutput(
            conversation_history=[],
            fallback_phase=state.fallback_phase,
            phone=state.phone,
            license_plate=state.license_plate,
            problem_summary=state.problem_summary,
            entry_problem=state.entry_problem
        )
