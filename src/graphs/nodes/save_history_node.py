"""
保存对话历史节点 - 用于多轮对话上下文和兜底流程状态
"""
import logging
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import SaveHistoryInput, SaveHistoryOutput
from storage.database.db import get_session
from storage.database.shared.model import ConversationHistory

logger = logging.getLogger(__name__)


def save_history_node(
    state: SaveHistoryInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> SaveHistoryOutput:
    """
    title: 保存对话历史
    desc: 将当前对话和兜底流程状态保存到数据库
    integrations: PostgreSQL
    """
    # 构建最新的 conversation_history（添加当前这一轮）
    updated_conversation_history = list(state.conversation_history) if state.conversation_history else []
    
    # 如果消息不为空，添加当前这一轮
    if state.user_message and state.reply_content:
        updated_conversation_history.append({
            "role": "user",
            "content": state.user_message
        })
        updated_conversation_history.append({
            "role": "assistant",
            "content": state.reply_content
        })
    
    # 如果没有 user_id，跳过保存到数据库，但还是返回最新的 conversation_history
    if not state.user_id:
        return SaveHistoryOutput(
            saved=True,
            conversation_history=updated_conversation_history,
            case_confirmed=state.case_confirmed if state.case_confirmed else False,
            negotiate_phase=state.negotiate_phase if state.negotiate_phase else "",
            problem_understanding=state.problem_understanding if state.problem_understanding else "",
            negotiate_round_count=state.negotiate_round_count if state.negotiate_round_count else 0,
            route_to_fallback=state.route_to_fallback if state.route_to_fallback else False
        )
    
    # 如果消息为空，跳过保存到数据库，但还是返回最新的 conversation_history
    if not state.user_message or not state.reply_content:
        return SaveHistoryOutput(
            saved=True,
            conversation_history=updated_conversation_history,
            case_confirmed=state.case_confirmed if state.case_confirmed else False,
            negotiate_phase=state.negotiate_phase if state.negotiate_phase else "",
            problem_understanding=state.problem_understanding if state.problem_understanding else "",
            negotiate_round_count=state.negotiate_round_count if state.negotiate_round_count else 0,
            route_to_fallback=state.route_to_fallback if state.route_to_fallback else False
        )
    
    session = None
    try:
        session = get_session()
        
        # 构建插入数据 - 【最终修复】直接给所有字段赋值，不管有没有条件
        record = ConversationHistory(
            user_id=state.user_id,
            user_message=state.user_message,
            reply_content=state.reply_content,
            intent=state.intent if state.intent else None,
            # 【最终修复】直接赋值所有兜底流程相关字段，不管有没有条件
            fallback_phase=state.fallback_phase if state.fallback_phase else None,
            phone=state.phone if state.phone else None,
            license_plate=state.license_plate if state.license_plate else None,
            problem_summary=state.problem_summary if state.problem_summary else None,
            entry_problem=state.entry_problem if state.entry_problem else None,
            user_supplement=state.user_supplement if state.user_supplement else None,
            conversation_truncate_index=state.conversation_truncate_index if state.conversation_truncate_index else None,
            case_confirmed=state.case_confirmed if state.case_confirmed else False,
            # 协商处理相关字段
            negotiate_phase=state.negotiate_phase if state.negotiate_phase else None,
            problem_understanding=state.problem_understanding if state.problem_understanding else None,
            negotiate_round_count=state.negotiate_round_count if state.negotiate_round_count else 0,
            route_to_fallback=state.route_to_fallback if state.route_to_fallback else False
        )
        
        # 如果 fallback_phase = "done"，表示兜底已完成，但我们不清空状态
        # 因为后面还需要经过 cond_fallback 节点来判断是否创建工单
        # 清空状态的动作放在 clear_fallback_state 节点中完成
        if state.fallback_phase == "done":
            logger.info(f"兜底流程完成，保留状态用于后续 cond_fallback 判断")
        
        # 【调试日志】打印 record 的内容
        logger.info(f"保存对话历史 - 准备保存的 record: fallback_phase={record.fallback_phase}, phone={record.phone}, license_plate={record.license_plate}, problem_summary={record.problem_summary}, entry_problem={record.entry_problem}")
        
        # 插入对话记录
        session.add(record)
        session.commit()
        
        logger.info(f"保存对话历史成功 - user_id: {state.user_id}, fallback_phase: {state.fallback_phase}")
        return SaveHistoryOutput(
            saved=True,
            conversation_history=updated_conversation_history,
            case_confirmed=state.case_confirmed if state.case_confirmed else False,
            negotiate_phase=state.negotiate_phase if state.negotiate_phase else "",
            problem_understanding=state.problem_understanding if state.problem_understanding else "",
            negotiate_round_count=state.negotiate_round_count if state.negotiate_round_count else 0,
            route_to_fallback=state.route_to_fallback if state.route_to_fallback else False
        )
        
    except Exception as e:
        # 保存失败不影响主流程，记录错误
        if session:
            session.rollback()
        logger.error(f"保存对话历史失败 - Exception: {type(e).__name__}: {e}")
        return SaveHistoryOutput(
            saved=False,
            conversation_history=updated_conversation_history,
            case_confirmed=state.case_confirmed if state.case_confirmed else False,
            negotiate_phase=state.negotiate_phase if state.negotiate_phase else "",
            problem_understanding=state.problem_understanding if state.problem_understanding else "",
            negotiate_round_count=state.negotiate_round_count if state.negotiate_round_count else 0,
            route_to_fallback=state.route_to_fallback if state.route_to_fallback else False
        )
    finally:
        if session:
            session.close()
