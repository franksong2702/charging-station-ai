"""
不满意处理节点 - 处理用户轻度不满的情况
AI 继续尝试帮助，同时记录不满意信息用于后续优化
"""
import logging

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import DissatisfiedInput, DissatisfiedOutput

# 配置日志
logger = logging.getLogger(__name__)


def dissatisfied_node(
    state: DissatisfiedInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> DissatisfiedOutput:
    """
    title: 轻度不满处理
    desc: 用户表达轻度不满时，道歉并请求详细描述问题，继续尝试帮助
    integrations: 无
    """
    ctx = runtime.context
    
    user_message = state.user_message.strip()
    
    logger.info(f"用户表达轻度不满: {user_message}")
    
    # 记录不满意信息到日志（后续由 save_record_node 保存到数据库）
    if state.conversation_history:
        # 提取原始问题（用户第一条消息）
        original_question = ""
        for msg in state.conversation_history:
            if msg.get("role") == "user" and msg.get("content"):
                original_question = msg["content"]
                break
        logger.info(f"不满意记录 - 原始问题: {original_question[:50] if original_question else 'N/A'}...")
        logger.info(f"不满意记录 - 不满意原因: {user_message}")
    
    # 构建回复：先道歉，再请求详细描述问题
    reply_content = """很抱歉没能帮到您 😔

您能再详细描述一下遇到的问题吗？我再尝试帮您解决。"""
    
    return DissatisfiedOutput(
        reply_content=reply_content,
        dissatisfied_logged=True
    )
