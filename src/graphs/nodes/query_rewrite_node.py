"""
查询改写节点 - 使用 LLM 将用户问题改写为更适合知识库检索的搜索词
基于意图信息，添加相关关键词，提高搜索精准度

优化点：
1. 移除 skip_rewrite_keywords 关键词列表
2. 使用 LLM 智能判断是否需要改写
3. 防止误判："谢谢你的帮助"不会被改写
"""
import os
import json
import logging
from jinja2 import Template

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import SystemMessage, HumanMessage

from graphs.state import QueryRewriteInput, QueryRewriteOutput

# 配置日志
logger = logging.getLogger(__name__)


def _should_rewrite_query(ctx, user_message: str) -> bool:
    """
    使用 LLM 判断用户消息是否需要改写为知识库检索词
    
    Args:
        ctx: 上下文
        user_message: 用户消息
        
    Returns:
        bool: 是否需要改写
    """
    try:
        prompt = f"""请判断以下用户消息是否需要改写为知识库检索词。

用户消息：{user_message}

【需要改写的情况】
- 用户提出了具体的充电桩使用问题（如"充电桩怎么扫码"、"优惠券怎么用"）
- 用户询问了具体的操作步骤或故障解决方法
- 用户消息包含实际的问题描述

【不需要改写的情况】
- 用户只是问候（如"你好"、"嗨"、"hello"）
- 用户只是感谢或告别（如"谢谢"、"再见"、"拜拜"）
- 用户只是简单的语气词（如"嗯"、"哦"、"啊"）
- 用户只是在闲聊，没有提出具体问题
- 用户消息太短（<5个字符），无法理解具体问题

【输出】
请返回 JSON 格式：
{{"should_rewrite": true/false, "reason": "判断理由"}}

请直接返回 JSON 格式，不要其他说明："""

        client = LLMClient(ctx=ctx)
        response = client.invoke(
            messages=[HumanMessage(content=prompt)],
            model="doubao-seed-1-8-251228",
            temperature=0.1,
            max_completion_tokens=50
        )
        
        # 提取回复内容
        content = response.content
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            result_text = "".join(text_parts).strip()
        else:
            result_text = str(content).strip()
        
        # 清理可能的 markdown 代码块
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = result_text.lstrip("```json").lstrip("```").rstrip("```").strip()
        
        # 解析 JSON
        result = json.loads(result_text)
        should_rewrite = result.get("should_rewrite", True)
        reason = result.get("reason", "")
        
        logger.info(f"LLM 判断是否改写: {should_rewrite}, 理由: {reason}")
        return should_rewrite
        
    except Exception as e:
        logger.error(f"LLM 判断是否改写失败: {str(e)}")
        # 失败时默认改写（保守策略）
        return True


def query_rewrite_node(
    state: QueryRewriteInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> QueryRewriteOutput:
    """
    title: 查询改写
    desc: 使用 LLM 将用户问题改写为更精准的搜索词，提高知识库检索效果
    integrations: 大语言模型
    """
    # 获取上下文
    ctx = runtime.context
    
    user_message = state.user_message.strip()
    intent = state.intent
    
    # ==================== 使用 LLM 判断是否需要改写 ====================
    # 移除关键词匹配，改用 LLM 智能判断
    should_rewrite = _should_rewrite_query(ctx, user_message)
    
    # 如果不需要改写，直接返回原始消息
    if not should_rewrite:
        logger.info(f"查询改写 - LLM 判断不需要改写，使用原始消息: {user_message}")
        return QueryRewriteOutput(rewritten_query=user_message)
    
    # ==================== 读取配置文件 ====================
    cfg_file = os.path.join(
        os.getenv("COZE_WORKSPACE_PATH", ""),
        config.get("configurable", {}).get("llm_cfg", "config/query_rewrite_llm_cfg.json")
    )
    
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)
    
    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")
    
    # ==================== 渲染提示词 ====================
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({
        "user_message": user_message,
        "intent": intent
    })
    
    # ==================== 调用 LLM ====================
    llm_client = LLMClient(ctx=ctx)
    
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]
    
    logger.info(f"查询改写 - 原始问题: {user_message}, 意图: {intent}")
    
    try:
        response = llm_client.invoke(
            messages=messages,
            model=llm_config.get("model", "doubao-seed-1-8-251228"),
            temperature=llm_config.get("temperature", 0.1),
            max_completion_tokens=llm_config.get("max_completion_tokens", 100)
        )
        
        # 提取回复内容
        content = response.content
        if isinstance(content, list):
            # 处理列表类型的内容
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            rewritten_query = "".join(text_parts).strip()
        else:
            rewritten_query = str(content).strip() if content else ""
        
        # 如果改写结果为空或过长，使用原始消息
        if not rewritten_query or len(rewritten_query) > 100:
            logger.warning(f"查询改写结果异常，使用原始消息: {rewritten_query}")
            rewritten_query = user_message
        
        logger.info(f"查询改写 - 改写结果: {rewritten_query}")
        
        return QueryRewriteOutput(rewritten_query=rewritten_query)
        
    except Exception as e:
        logger.error(f"查询改写失败: {str(e)}")
        # 失败时使用原始消息
        return QueryRewriteOutput(rewritten_query=user_message)
