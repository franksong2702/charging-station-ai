"""
查询改写节点 - 使用 LLM 将用户问题改写为更适合知识库检索的搜索词
基于意图信息，添加相关关键词，提高搜索精准度
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
