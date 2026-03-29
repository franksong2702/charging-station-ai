"""
不满意处理节点 - 处理用户表达不满的情况
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
    title: 不满意处理
    desc: 用户表达不满时，请求用户详细描述问题，再次尝试帮助
    integrations: 无
    """
    ctx = runtime.context
    
    user_message = state.user_message.strip()
    
    logger.info(f"用户表达不满: {user_message}")
    
    # 构建回复：先道歉，再请求详细描述问题
    reply_content = """很抱歉没能帮到您 😔

您能再详细描述一下遇到的问题吗？我再尝试帮您解决。"""
    
    return DissatisfiedOutput(
        reply_content=reply_content,
        dissatisfied_logged=True
    )
