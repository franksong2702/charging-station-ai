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
                top_k=5,
                min_score=0.3  # 降低阈值，增加匹配概率
            )
            
            if search_response.code == 0 and search_response.chunks:
                for chunk in search_response.chunks:
                    chunk_dict = {
                        "content": chunk.content,
                        "score": chunk.score,
                        "doc_id": chunk.doc_id
                    }
                    knowledge_chunks.append(chunk_dict)
                    knowledge_context += f"\n{chunk.content}\n"
                
                logger.info(f"知识库搜索成功，找到 {len(knowledge_chunks)} 条相关内容")
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
    
    # 如果知识库搜索失败，使用降级方案
    if not kb_success:
        logger.warning("知识库搜索失败，使用降级方案：直接LLM回答")
        # 使用降级系统提示词
        fallback_sp = """你是一个充电桩智能客服助手。

你的职责是：
1. 帮助用户解决充电桩使用问题
2. 提供充电桩操作指导
3. 处理用户的故障咨询

回复要求：
- 友好、专业、简洁
- 如果不确定具体问题，请引导用户描述更详细的情况
- 如果涉及投诉、退款等问题，建议用户联系人工客服

请根据用户的问题，尽力提供帮助。"""
        
        fallback_up = f"""用户问题：{state.user_message}

问题类型：{state.intent}

请帮助用户解决问题。如果问题不在你的知识范围内，请引导用户联系人工客服。"""
        
        sp = fallback_sp
        up = fallback_up
        knowledge_context = "（知识库暂时不可用）"
    
    # 渲染提示词
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({
        "user_message": state.user_message,
        "knowledge_context": knowledge_context,
        "intent": state.intent
    })
    
    # 初始化 LLM 客户端
    llm_client = LLMClient(ctx=ctx)
    
    # 构建消息（包含对话历史，但限制长度）
    messages = [SystemMessage(content=sp)]
    
    # 添加对话历史（限制为最近6条，避免历史过长干扰回答）
    if state.conversation_history:
        # 只保留最近6条消息（3轮对话）
        recent_history = state.conversation_history[-6:] if len(state.conversation_history) > 6 else state.conversation_history
        logger.info(f"加载对话历史，共 {len(state.conversation_history)} 条，使用最近 {len(recent_history)} 条")
        for msg in recent_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
    
    # 添加当前用户消息
    messages.append(HumanMessage(content=user_prompt_content))
    
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
