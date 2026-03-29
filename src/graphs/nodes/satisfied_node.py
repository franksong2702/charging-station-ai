"""
满意处理节点 - 用户表达满意时，感谢用户并请求评价
"""
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import DissatisfiedInput, DissatisfiedOutput


def satisfied_node(
    state: DissatisfiedInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> DissatisfiedOutput:
    """
    title: 满意处理
    desc: 用户表达满意时，感谢用户并请求评价
    """
    ctx = runtime.context
    
    # 构建回复：感谢用户 + 请求评价
    reply_content = """不客气，很高兴能帮到您！😊

如果您还有其他充电桩相关的问题，欢迎随时问我～

───────────
**请问这个回答对您有帮助吗？**

👍 有帮助
👎 没有帮助"""
    
    return DissatisfiedOutput(
        reply_content=reply_content,
        dissatisfied_logged=False
    )
