"""
清除兜底状态节点 - 在兜底流程完成后清除状态
"""
import os
import json
import logging
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from jinja2 import Template
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import HumanMessage

from graphs.state import ClearFallbackStateInput, ClearFallbackStateOutput
from storage.database.db import get_session
from storage.database.shared.model import ConversationHistory

# 配置日志
logger = logging.getLogger(__name__)


def _recognize_intent_for_exit(ctx, user_message: str, config: RunnableConfig) -> str:
    """
    当用户退出兜底流程时，重新识别用户意图
    """
    # 简单的意图识别（不依赖完整的 LLM 调用）
    user_message = user_message.strip()
    
    # 故障关键词
    fault_keywords = ["充不进去", "充不上", "充不进", "充不了", "充电失败", 
                      "拔不出来", "停不下来", "充电慢", "坏了", "故障"]
    for keyword in fault_keywords:
        if keyword in user_message:
            return "fault_handling"
    
    # 默认返回使用指导
    return "usage_guidance"


def clear_fallback_state_node(
    state: ClearFallbackStateInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> ClearFallbackStateOutput:
    """
    title: 清除兜底状态
    desc: 兜底流程完成后或用户退出兜底时，清除用户的兜底状态
    integrations: PostgreSQL
    """
    ctx = runtime.context
    
    # 识别用户的真实意图（用于后续处理）
    new_intent = _recognize_intent_for_exit(ctx, state.user_message or "", config)
    
    if not state.user_id:
        logger.info("无用户ID，跳过清除状态")
        return ClearFallbackStateOutput(
            cleared=True,
            fallback_phase="",
            phone="",
            license_plate="",
            problem_summary="",
            case_confirmed=False,
            intent=new_intent
        )
    
    try:
        session = get_session()
        
        # 保存一条空状态，覆盖之前的兜底状态
        # 如果 user_message 和 reply_content 为空，说明是兜底完成后的自动清除
        record = ConversationHistory(
            user_id=state.user_id,
            user_message=state.user_message or "",
            reply_content=state.reply_content or "",
            intent="" if not state.user_message else "",
            fallback_phase="",  # 清空兜底状态
            phone="",
            license_plate="",
            problem_summary="",
            entry_problem="",
            user_supplement=""
        )
        
        session.add(record)
        session.commit()
        session.close()
        
        logger.info(f"已清除用户 {state.user_id} 的兜底状态，新意图: {new_intent}")
        return ClearFallbackStateOutput(
            cleared=True,
            fallback_phase="",
            phone="",
            license_plate="",
            problem_summary="",
            case_confirmed=False,
            intent=new_intent
        )
        
    except Exception as e:
        logger.error(f"清除兜底状态失败: {str(e)}")
        return ClearFallbackStateOutput(
            cleared=False,
            fallback_phase="",
            phone="",
            license_plate="",
            problem_summary="",
            case_confirmed=False,
            intent=new_intent
        )
