"""
ASR 语音转文字节点 - 将语音转换为文字
"""
import logging

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import ASRClient

from graphs.state import ASRInput, ASROutput

# 配置日志
logger = logging.getLogger(__name__)


def asr_node(
    state: ASRInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> ASROutput:
    """
    title: 语音转文字
    desc: 调用 ASR 服务将语音 URL 转换为文字
    integrations: ASR 语音识别
    """
    ctx = runtime.context
    
    voice_url = state.voice_url
    logger.info(f"开始语音识别，voice_url: {voice_url[:50]}...")
    
    try:
        # 初始化 ASR 客户端
        asr_client = ASRClient(ctx=ctx)
        
        # 调用 ASR 识别
        transcribed_text, data = asr_client.recognize(
            uid="charging_bot_user",
            url=voice_url
        )
        
        # 提取转写文字
        if transcribed_text:
            logger.info(f"语音识别成功: {transcribed_text[:100]}...")
            return ASROutput(user_message=transcribed_text.strip())
        else:
            logger.warning("语音识别返回空结果")
            return ASROutput(user_message="")
            
    except Exception as e:
        logger.error(f"语音识别失败: {str(e)}")
        # 返回空文字，后续流程会处理
        return ASROutput(user_message="")
