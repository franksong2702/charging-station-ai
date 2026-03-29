"""
评价反馈节点 - 处理用户的评价反馈
"""
import logging

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import FeedbackInput, FeedbackOutput

# 配置日志
logger = logging.getLogger(__name__)


def feedback_node(
    state: FeedbackInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> FeedbackOutput:
    """
    title: 评价反馈处理
    desc: 处理用户提交的评价反馈（很好/没有帮助）
    integrations: 无
    """
    ctx = runtime.context
    
    user_message = state.user_message.strip()
    
    # 判断评价类型（支持半角/全角数字）
    feedback_type = "unknown"
    if user_message in ["1", "１", "【1】", "【１】", "很好", "满意", "有帮助"]:
        feedback_type = "good"
        reply_content = "感谢您的反馈！我们会继续努力为您提供更好的服务 😊"
    elif user_message in ["2", "２", "【2】", "【２】", "没有帮助", "不满意", "没用"]:
        feedback_type = "bad"
        reply_content = "感谢您的反馈！很抱歉没能帮到您。您能再详细描述一下遇到的问题吗？我再尝试帮您解决。"
    else:
        feedback_type = "unknown"
        reply_content = "感谢您的反馈！"
    
    logger.info(f"收到用户评价: {feedback_type}")
    
    return FeedbackOutput(
        feedback_type=feedback_type,
        reply_content=reply_content
    )
