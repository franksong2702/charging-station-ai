"""
知识库问答节点 - 基于知识库回答用户问题，支持多轮对话上下文
"""
import os
import json
import time
import logging
from typing import List, Dict, Any

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import KnowledgeClient, LLMClient, Config
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from jinja2 import Template

from graphs.state import KnowledgeQAInput, KnowledgeQAOutput

# 配置日志
logger = logging.getLogger(__name__)


def _search_knowledge_with_retry(
    knowledge_client: KnowledgeClient,
    query: str,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> tuple:
    """
    带重试的知识库搜索
    
    Args:
        knowledge_client: 知识库客户端
        query: 搜索查询
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
    
    Returns:
        (knowledge_chunks, knowledge_context, success)
    """
    knowledge_chunks = []
    knowledge_context = ""
    
    for attempt in range(max_retries):
        try:
            logger.info(f"知识库搜索尝试 {attempt + 1}/{max_retries}: {query[:50]}...")
            
            search_response = knowledge_client.search(
                query=query,
                top_k=3,  # 取前3条，确保能匹配到
                min_score=0.3
            )
            
            if search_response.code == 0 and search_response.chunks:
                # 只使用第一条（最相关的）
                chunk = search_response.chunks[0]
                chunk_dict = {
                    "content": chunk.content,
                    "score": chunk.score,
                    "doc_id": chunk.doc_id
                }
                knowledge_chunks.append(chunk_dict)
                knowledge_context = chunk.content  # 只使用一条内容
                
                logger.info(f"知识库搜索成功，找到相关内容，得分: {chunk.score:.2f}")
                return knowledge_chunks, knowledge_context, True
            else:
                logger.warning(f"知识库搜索返回空结果: code={search_response.code}")
                return knowledge_chunks, knowledge_context, True  # 搜索成功但无结果
                
        except Exception as e:
            logger.warning(f"知识库搜索失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error(f"知识库搜索最终失败: {str(e)}")
                return knowledge_chunks, knowledge_context, False
    
    return knowledge_chunks, knowledge_context, False


def knowledge_qa_node(
    state: KnowledgeQAInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> KnowledgeQAOutput:
    """
    title: 知识库问答
    desc: 根据用户问题搜索知识库，生成专业回复
    integrations: 大语言模型, 知识库
    """
    # 获取上下文
    ctx = runtime.context
    
    # 初始化知识库客户端
    knowledge_client = KnowledgeClient(config=Config(), ctx=ctx)
    
    # 搜索知识库（带重试机制）
    knowledge_chunks, knowledge_context, kb_success = _search_knowledge_with_retry(
        knowledge_client=knowledge_client,
        query=state.user_message,
        max_retries=3,
        retry_delay=1.0
    )
    
    # 读取 LLM 配置
    cfg_file = os.path.join(
        os.getenv("COZE_WORKSPACE_PATH", ""),
        config.get("configurable", {}).get("llm_cfg", "config/knowledge_qa_llm_cfg.json")
    )
    
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)
    
    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")
    
    # 如果知识库搜索失败或无结果，使用降级方案
    if not kb_success or not knowledge_context:
        logger.warning("知识库搜索失败或无结果，使用降级方案：直接LLM回答")
        # 使用降级系统提示词
        fallback_sp = """你是充电桩客服。回答规则：
1. 简洁明了，不超过50字
2. 如果是使用问题，告诉用户基本流程：解锁充电口→扫码→插枪→充电
3. 如果是故障问题，建议联系现场工作人员
4. 返回JSON格式：{"reply_content": "回答"}"""
        
        fallback_up = f"""用户问题：{state.user_message}

请简洁回答，返回JSON。"""
        
        sp = fallback_sp
        up = fallback_up
        knowledge_context = ""
    
    # 渲染提示词
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({
        "user_message": state.user_message,
        "knowledge_context": knowledge_context,
        "intent": state.intent
    })
    
    # 初始化 LLM 客户端
    llm_client = LLMClient(ctx=ctx)
    
    # 构建消息（不使用对话历史，避免干扰）
    # 每次回答都是独立的，基于当前问题和知识库
    messages = [SystemMessage(content=sp), HumanMessage(content=user_prompt_content)]
    
    # 调用 LLM（带重试）
    max_llm_retries = 3
    response = None
    
    for attempt in range(max_llm_retries):
        try:
            response = llm_client.invoke(
                messages=messages,
                model=llm_config.get("model", "doubao-seed-1-8-251228"),
                temperature=llm_config.get("temperature", 0.7),
                max_completion_tokens=llm_config.get("max_completion_tokens", 1000)
            )
            break
        except Exception as e:
            logger.warning(f"LLM调用失败 (尝试 {attempt + 1}/{max_llm_retries}): {str(e)}")
            if attempt < max_llm_retries - 1:
                time.sleep(1.0)
            else:
                # LLM 也失败了，返回默认回复
                logger.error(f"LLM调用最终失败: {str(e)}")
                return KnowledgeQAOutput(
                    reply_content="抱歉，系统暂时繁忙，请稍后再试。如需紧急帮助，请联系人工客服。",
                    knowledge_chunks=[]
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
        raw_content = " ".join(text_parts).strip()
    else:
        raw_content = str(content).strip()
    
    # 解析 JSON 格式的回复
    reply_content = ""
    should_ask_feedback = False
    
    # 尝试解析 JSON
    try:
        # 清理可能的 markdown 代码块标记
        json_str = raw_content.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()
        
        result = json.loads(json_str)
        if isinstance(result, dict):
            reply_content = result.get("reply_content", "")
            should_ask_feedback = result.get("should_ask_feedback", False)
            logger.info(f"LLM 判断是否请求评价: {should_ask_feedback}")
        else:
            reply_content = raw_content
            should_ask_feedback = False
    except json.JSONDecodeError:
        # JSON 解析失败，直接使用原始内容
        logger.warning(f"JSON 解析失败，使用原始回复: {raw_content[:100]}...")
        reply_content = raw_content
        should_ask_feedback = False
    
    # 如果 LLM 判断应该请求评价，添加评价提示
    if should_ask_feedback:
        feedback_prompt = """

───────────
您对本次回答满意吗？
回复【1】很好
回复【2】没有帮助"""
        reply_content_with_feedback = reply_content + feedback_prompt
        logger.info("已添加评价提示")
    else:
        reply_content_with_feedback = reply_content
        logger.info("不添加评价提示（LLM 判断不需要）")
    
    return KnowledgeQAOutput(
        reply_content=reply_content_with_feedback,
        knowledge_chunks=knowledge_chunks,
        need_feedback=should_ask_feedback
    )
