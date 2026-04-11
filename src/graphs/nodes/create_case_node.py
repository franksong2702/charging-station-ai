"""
创建工单节点 - 将确认后的问题创建为工单记录
"""
import logging
from typing import List, Dict, Any

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import CreateCaseInput, CreateCaseOutput
from storage.database.db import get_session
from storage.database.shared.model import CaseRecord

# 配置日志
logger = logging.getLogger(__name__)


def create_case_node(
    state: CreateCaseInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> CreateCaseOutput:
    """
    title: 创建工单
    desc: 将确认后的问题创建为工单记录，用于客服跟进
    integrations: PostgreSQL
    """
    ctx = runtime.context
    
    logger.info(f"创建工单 - 手机号: {state.phone}, 车牌号: {state.license_plate}")
    logger.info(f"创建工单 - 问题总结: {state.problem_summary[:50]}...")
    
    session = None
    try:
        session = get_session()
        
        # 构建工单数据
        case_record = CaseRecord(
            user_id=state.user_id if state.user_id else None,
            phone=state.phone,
            license_plate=state.license_plate,
            problem_summary=state.problem_summary,
            conversation_context=state.conversation_history if state.conversation_history else [],
            case_type="fallback",  # 兜底场景
            status="pending"
        )
        
        # 插入工单记录
        session.add(case_record)
        session.commit()
        
        # 获取工单ID
        case_id = str(case_record.id)
        
        logger.info(f"工单创建成功 - 工单ID: {case_id}")
        
        return CreateCaseOutput(
            case_created=True,
            case_id=case_id,
            reply_content=state.reply_content  # 保留回复内容
        )
        
    except Exception as e:
        if session:
            session.rollback()
        logger.error(f"创建工单失败: {str(e)}")
        return CreateCaseOutput(
            case_created=False,
            case_id="",
            reply_content=state.reply_content  # 即使失败也保留回复内容
        )
    finally:
        if session:
            session.close()
