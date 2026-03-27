"""
输入预处理节点 - 判断输入类型并预处理
"""
import logging

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import InputProcessInput, InputProcessOutput

# 配置日志
logger = logging.getLogger(__name__)


def input_process_node(
    state: InputProcessInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> InputProcessOutput:
    """
    title: 输入预处理
    desc: 判断用户输入是文字还是语音，如果是语音则标记需要 ASR 处理
    integrations: 无
    """
    ctx = runtime.context
    
    user_message = state.user_message or ""
    voice_url = state.voice_url or ""
    
    logger.info(f"输入预处理 - 文字: {user_message[:50] if user_message else '无'}, 语音URL: {'有' if voice_url else '无'}")
    
    # 此节点仅用于判断分支，不修改状态
    return InputProcessOutput(processed=True)
