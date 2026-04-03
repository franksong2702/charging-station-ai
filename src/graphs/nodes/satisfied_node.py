"""
满意处理节点 - 用户表达满意时，感谢用户并请求评价
"""
import logging
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import SatisfiedInput, SatisfiedOutput

# 配置日志
logger = logging.getLogger(__name__)


def satisfied_node(
    state: SatisfiedInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> SatisfiedOutput:
    """
    title: 满意处理
    desc: 用户表达满意时，感谢用户并请求评价
    integrations: 无
    """
    ctx = runtime.context
    
    user_message = state.user_message.strip()
    logger.info(f"用户表达满意: {user_message}")
    
    # 根据用户的感谢语选择回复
    if "谢谢" in user_message or "感谢" in user_message:
        thanks_reply = "不客气，很高兴能帮到您！😊"
    elif "好的" in user_message:
        thanks_reply = "好的，有任何问题随时问我！😊"
    else:
        thanks_reply = "感谢您的认可！😊"
    
    # 构建回复：感谢用户 + 请求评价
    reply_content = f"""{thanks_reply}

如果您还有其他充电桩相关的问题，欢迎随时问我～

───────────
请问这个回答对您有帮助吗？
1. 有帮助
2. 没有帮助"""
    
    return SatisfiedOutput(
        reply_content=reply_content,
        satisfied_logged=True
    )
