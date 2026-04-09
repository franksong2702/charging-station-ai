"""
Summary Agent - 生成详细的问题总结

核心原则：
1. 总结要详细，包含原因（如"因为优惠券没使用，所以多扣了钱要求退款"）
2. 总结后让用户确认
3. 用户纠正就更新
"""
import os
import json
import logging
import re

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from tools.llm import create_llm_client
from langchain_core.messages import HumanMessage

from graphs.state import SummaryInput, SummaryOutput

logger = logging.getLogger(__name__)


def summary_agent_node(
    state: SummaryInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> SummaryOutput:
    """
    title: Summary Agent - 生成详细问题总结
    desc: 根据对话历史生成详细的问题总结，包含原因和诉求
    integrations: 大语言模型
    """
    ctx = runtime.context
    conversation_history = state.conversation_history or []
    
    logger.info(f"Summary Agent - 生成问题总结")
    
    # 构建对话历史
    history_text = ""
    if conversation_history:
        for i, msg in enumerate(conversation_history[-10:], 1):  # 最近 5 轮
            role = "用户" if i % 2 == 1 else "AI"
            history_text += f"{role}: {msg.get('content', '')}\n"
    
    # 调用 LLM 生成详细总结
    prompt = f"""你是一个专业的客服助手。请根据对话历史生成详细的问题总结。

【对话历史】
{history_text}

【任务】
生成详细的问题总结，包含：
1. 用户遇到了什么问题
2. 问题的原因是什么（如果有提到）
3. 用户的诉求是什么（退款、赔偿、维修等）

【输出格式】
请返回 JSON 格式：
{{
    "detailed_summary": "详细总结（包含原因，如'因为优惠券未成功使用，导致多扣了 10 元钱，用户要求退款'）",
    "simple_problem": "简单问题（如'退款'）"
}}

请直接返回 JSON 格式，不要其他说明："""

    try:
        client = create_llm_client(ctx=ctx, provider="doubao")
        response = client.invoke(
            messages=[HumanMessage(content=prompt)],
            model="doubao-seed-1-8-251228",
            temperature=0.2,
            max_completion_tokens=200
        )
        
        # 解析 LLM 返回
        content = str(response.content).strip()
        if content.startswith("```"):
            content = re.sub(r'^```json?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
        
        result = json.loads(content)
        
        detailed_summary = result.get("detailed_summary", "")
        simple_problem = result.get("simple_problem", "")
        
        logger.info(f"Summary Agent - 详细总结：{detailed_summary}")
        
        return SummaryOutput(
            detailed_summary=detailed_summary,
            simple_problem=simple_problem
        )
        
    except Exception as e:
        logger.error(f"Summary Agent 失败：{e}")
        return SummaryOutput(
            detailed_summary="",
            simple_problem=""
        )
