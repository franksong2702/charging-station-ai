"""
清除兜底状态节点 - 在兜底流程完成后清除状态
"""
import logging
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from postgrest.exceptions import APIError

from graphs.state import ClearFallbackStateInput, ClearFallbackStateOutput
from storage.database.supabase_client import get_supabase_client

# 配置日志
logger = logging.getLogger(__name__)


def clear_fallback_state_node(
    state: ClearFallbackStateInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> ClearFallbackStateOutput:
    """
    title: 清除兜底状态
    desc: 兜底流程完成后，清除用户的状态，以便下次正常对话
    integrations: Supabase
    """
    if not state.user_id:
        logger.info("无用户ID，跳过清除状态")
        return ClearFallbackStateOutput(cleared=True)
    
    try:
        client = get_supabase_client()
        
        # 保存一条空状态，覆盖之前的兜底状态
        client.table("conversation_history").insert({
            "user_id": state.user_id,
            "user_message": state.user_message or "",
            "reply_content": state.reply_content or "",
            "intent": "",
            "fallback_phase": "",  # 清空兜底状态
            "phone": "",
            "license_plate": "",
            "problem_summary": ""
        }).execute()
        
        logger.info(f"已清除用户 {state.user_id} 的兜底状态")
        return ClearFallbackStateOutput(cleared=True)
        
    except Exception as e:
        logger.error(f"清除兜底状态失败: {str(e)}")
        return ClearFallbackStateOutput(cleared=False)
