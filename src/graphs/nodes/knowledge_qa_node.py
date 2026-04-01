"""
知识库问答节点 - 基于知识库回答用户问题，支持多轮对话上下文
优化：多轮搜索策略，优先返回完整答案而非标题片段
"""
import os
import re
import json
import time
import logging
from typing import List, Dict, Any, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import KnowledgeClient, LLMClient, Config
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from jinja2 import Template

from graphs.state import KnowledgeQAInput, KnowledgeQAOutput

# 配置日志
logger = logging.getLogger(__name__)


def _is_valid_answer_content(content: str) -> bool:
    """
    判断内容是否是有效的答案（而非只是标题或关键词）
    
    有效答案特征：
    - 包含"简短回答"关键词（优先级最高）
    - 包含具体操作指引（如位置描述）
    - 内容长度足够（超过20字符）
    - 不是纯标题（不以####开头）
    - 不是纯关键词列表
    - 不是特征描述（如"黑白二维码，旁边有Tesla标识"）
    """
    if not content:
        return False
    
    content_stripped = content.strip()
    
    # 纯标题（只有 #### 标题）不算有效答案
    if content_stripped.startswith("####"):
        return False
    
    # 纯关键词列表不算有效答案
    if content_stripped.startswith("**关键词**"):
        return False
    
    # 标题结尾是冒号或问号的，通常是标题而非答案
    if content_stripped.endswith("：") or content_stripped.endswith(":"):
        return False
    if content_stripped.endswith("？") or content_stripped.endswith("?"):
        return False
    
    # 内容太短（<20字符）不算有效答案
    if len(content_stripped) < 20:
        return False
    
    # 特征描述不算有效答案
    if "**二维码特征**" in content:
        return False
    
    # 包含"简短回答"关键词，是有效答案（优先级最高）
    if "**简短回答**" in content:
        return True
    
    # 包含完整指引内容
    if "找到二维码" in content:
        return True
    
    # 扫码位置指引，但需要包含具体位置且不是特征描述
    if "**扫码位置**" in content and len(content_stripped) > 25:
        return True
    
    return False


def _extract_brand_keywords(query: str) -> List[str]:
    """
    从用户问题中提取品牌关键词
    """
    brands = []
    brand_map = {
        "特斯拉": ["特斯拉", "tesla", "Tesla"],
        "比亚迪": ["比亚迪", "byd", "BYD"],
        "蔚来": ["蔚来", "nio", "NIO"],
        "小鹏": ["小鹏", "xpeng", "XPeng"],
        "理想": ["理想", "li auto", "Li Auto"]
    }
    
    query_lower = query.lower()
    for brand, keywords in brand_map.items():
        for kw in keywords:
            if kw.lower() in query_lower:
                brands.append(brand)
                break
    
    return brands


def _enhance_query(query: str) -> List[str]:
    """
    增强搜索查询，生成多个搜索变体
    目标：提高完整答案的匹配度
    """
    queries = [query]  # 原始查询
    
    # 提取品牌关键词
    brands = _extract_brand_keywords(query)
    
    # 品牌特定的答案关键词
    brand_answer_keywords = {
        "特斯拉": ["充电桩正面", "黑白二维码"],
        "比亚迪": ["充电桩侧面", "彩色二维码"],
    }
    
    # 如果问题是"怎么充电"类，添加位置相关关键词
    if "充电" in query and ("怎么" in query or "如何" in query):
        if brands:
            for brand in brands:
                # 只添加与品牌相关的特定查询
                keywords = brand_answer_keywords.get(brand, [])
                if keywords:
                    queries.append(f"{brand} 简短回答 {' '.join(keywords)}")
                    queries.append(f"{brand} 扫码位置 {' '.join(keywords)}")
    
    # 如果问题包含"扫码"，添加位置关键词
    if "扫码" in query or "二维码" in query:
        if brands:
            for brand in brands:
                keywords = brand_answer_keywords.get(brand, [])
                if keywords:
                    queries.append(f"{brand} 扫码位置 简短回答 {' '.join(keywords)}")
    
    # 故障处理类问题的增强查询
    fault_keywords = ["充不进去", "充不上", "充不进", "充不了", "充不起", 
                      "充电失败", "无法充电", "无法启动"]
    if any(kw in query for kw in fault_keywords):
        queries.append("无法充电 检查 充电枪 插好 简短回答")
    
    # 充电枪拔不出来
    if "拔不出来" in query or "卡住" in query:
        queries.append("充电枪 卡住 拔出 解锁 车辆 联系客服 简短回答")
    
    # 第一次使用类问题
    if "第一次" in query or "新手" in query or "怎么用" in query:
        queries.append(f"{query} 完整流程 简短回答")
    
    return queries


def _search_single_query(
    knowledge_client: KnowledgeClient,
    query: str,
    min_score: float = 0.5,
    top_k: int = 5
) -> Optional[Any]:
    """
    执行单次知识库搜索
    """
    try:
        search_response = knowledge_client.search(
            query=query,
            top_k=top_k,
            min_score=min_score
        )
        
        if search_response.code == 0 and search_response.chunks:
            return search_response
        return None
    except Exception as e:
        logger.warning(f"知识库搜索异常: {str(e)}")
        return None


def _search_knowledge_with_retry(
    knowledge_client: KnowledgeClient,
    query: str,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> tuple:
    """
    带重试和多策略的知识库搜索
    
    搜索策略：
    1. 先用原始查询搜索
    2. 如果结果不理想（得分低或只是标题），用增强查询再搜索
    3. 优先返回包含完整答案的内容
    
    Args:
        knowledge_client: 知识库客户端
        query: 搜索查询
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
    
    Returns:
        (knowledge_chunks, knowledge_context, success)
    """
    knowledge_chunks: List[Dict[str, Any]] = []
    knowledge_context = ""
    
    # 生成增强查询列表
    enhanced_queries = _enhance_query(query)
    logger.info(f"搜索查询列表: {enhanced_queries}")
    
    all_results: List[Dict[str, Any]] = []
    
    # 执行多次搜索，收集结果
    for search_query in enhanced_queries[:3]:  # 最多使用3个查询变体
        for attempt in range(max_retries):
            response = _search_single_query(knowledge_client, search_query, min_score=0.5, top_k=5)
            
            if response and response.chunks:
                for chunk in response.chunks:
                    # 避免重复
                    chunk_id = chunk.chunk_id
                    if not any(r.get("chunk_id") == chunk_id for r in all_results):
                        all_results.append({
                            "content": chunk.content,
                            "score": chunk.score,
                            "doc_id": chunk.doc_id,
                            "chunk_id": chunk_id,
                            "query": search_query
                        })
                break  # 搜索成功，跳出重试循环
            else:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
    
    if not all_results:
        logger.warning("所有搜索策略均无结果")
        return knowledge_chunks, knowledge_context, True
    
    # 按得分排序
    all_results.sort(key=lambda x: x["score"], reverse=True)
    
    # 优先选择有效答案内容
    best_result = None
    for result in all_results:
        if _is_valid_answer_content(result["content"]):
            best_result = result
            logger.info(f"找到有效答案，得分: {result['score']:.2f}, 内容: {result['content'][:50]}...")
            break
    
    # 如果没有找到有效答案，使用得分最高的结果
    if not best_result:
        best_result = all_results[0]
        logger.info(f"使用最高得分结果，得分: {best_result['score']:.2f}, 内容: {best_result['content'][:50]}...")
    
    # 如果得分太低（< 0.6），可能不够相关
    if best_result["score"] < 0.6:
        logger.warning(f"最佳结果得分较低 ({best_result['score']:.2f})，可能不够相关")
    
    knowledge_chunks = [{
        "content": best_result["content"],
        "score": best_result["score"],
        "doc_id": best_result["doc_id"]
    }]
    knowledge_context = best_result["content"]
    
    return knowledge_chunks, knowledge_context, True


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
