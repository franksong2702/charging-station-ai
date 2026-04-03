"""
创建工单节点 - 将确认后的问题创建为工单记录
"""
import logging
from typing import List, Dict, Any

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from postgrest.exceptions import APIError

from graphs.state import CreateCaseInput, CreateCaseOutput
from storage.database.supabase_client import get_supabase_client

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
    integrations: Supabase
    """
    ctx = runtime.context
    
    logger.info(f"创建工单 - 手机号: {state.phone}, 车牌号: {state.license_plate}")
    logger.info(f"创建工单 - 问题总结: {state.problem_summary[:50]}...")
    
    try:
        client = get_supabase_client()
        
        # 构建工单数据
        case_data = {
            "user_id": state.user_id if state.user_id else None,
            "phone": state.phone,
            "license_plate": state.license_plate,
            "problem_summary": state.problem_summary,
            "conversation_context": state.conversation_history if state.conversation_history else [],
            "case_type": "fallback",  # 兜底场景
            "status": "pending"
        }
        
        # 插入工单记录
        result = client.table("case_records").insert(case_data).execute()
        
        # 获取工单ID
        case_id = ""
        result_data = result.data
        if result_data and isinstance(result_data, list) and len(result_data) > 0:
            first_record = result_data[0]
            if isinstance(first_record, dict):
                case_id = str(first_record.get("id", ""))
        
        logger.info(f"工单创建成功 - 工单ID: {case_id}")
        
        return CreateCaseOutput(
            case_created=True,
            case_id=case_id
        )
        
    except APIError as e:
        logger.error(f"创建工单失败: {e.message}")
        return CreateCaseOutput(
            case_created=False,
            case_id=""
        )
    except Exception as e:
        logger.error(f"创建工单失败: {str(e)}")
        return CreateCaseOutput(
            case_created=False,
            case_id=""
        )
