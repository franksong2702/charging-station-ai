"""
加载对话历史节点 - 用于多轮对话上下文和兜底流程状态
"""
import logging
from datetime import datetime, timedelta
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

# 兜底流程状态过期时间（30分钟）
FALLBACK_STATE_EXPIRE_MINUTES = 30


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
    
    session = None
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
        conversation_truncate_index = 0
        
        if latest_record:
            fallback_phase = str(latest_record.fallback_phase or "")
            phone = str(latest_record.phone or "")
            license_plate = str(latest_record.license_plate or "")
            problem_summary = str(latest_record.problem_summary or "")
            entry_problem = str(latest_record.entry_problem or "")
            conversation_truncate_index = int(latest_record.conversation_truncate_index or 0)
            
            # 【新增：检查兜底流程状态是否过期
            if fallback_phase and latest_record.created_at:
                try:
                    # 计算时间差 - 处理时区问题
                    record_time = latest_record.created_at
                    # 如果数据库时间带时区，转换为 naive（去掉时区）
                    if record_time.tzinfo is not None:
                        record_time = record_time.replace(tzinfo=None)
                    # 当前时间也用 naive
                    now_time = datetime.now()
                    
                    time_diff = now_time - record_time
                    if time_diff > timedelta(minutes=FALLBACK_STATE_EXPIRE_MINUTES):
                        # 超过 30 分钟，重置兜底流程状态
                        logger.info(f"兜底流程状态已过期（{time_diff.total_seconds()/60:.1f}分钟），已重置")
                        fallback_phase = ""
                        phone = ""
                        license_plate = ""
                        problem_summary = ""
                        entry_problem = ""
                except Exception as e:
                    # 时间计算出错，不影响主流程，记录日志即可
                    logger.warning(f"检查兜底流程状态过期失败: {type(e).__name__}: {e}")
        
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
        if state.conversation_truncate_index:
            conversation_truncate_index = state.conversation_truncate_index
        
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
            entry_problem=entry_problem,
            conversation_truncate_index=conversation_truncate_index
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
    finally:
        if session:
            session.close()
