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
from coze_coding_dev_sdk import KnowledgeClient, Config
from tools.llm import create_llm_client
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from jinja2 import Template

from graphs.state import KnowledgeQAInput, KnowledgeQAOutput

# 知识库数据集配置 - 使用v1.3版本
KNOWLEDGE_TABLE_NAMES = ["charging_station_kb_v1_3"]

# 配置日志
logger = logging.getLogger(__name__)


def _is_valid_answer_content(content: str) -> bool:
    """
    判断内容是否是有效的答案（而非只是标题或关键词）
    
    有效答案特征：
    - 包含"简短回答"关键词（优先级最高）
    - 包含具体操作指引（如位置描述）
    - 包含具体信息（如时间、费用、步骤等）
    - 内容长度足够（超过20字符）
    - 不是纯标题（不以####开头）
    - 不是纯关键词列表
    - 不是特征描述（如"黑白二维码，旁边有Tesla标识"）
    - 不是空片段或 nan 值
    - 不是填写说明/注释
    """
    if not content:
        return False
    
    content_stripped = content.strip()
    
    # 过滤 nan 值（Excel 空单元格导入）
    if content_stripped.lower() == "nan":
        return False
    
    # 过滤包含 nan 的无效内容
    if content_stripped == "nan" or content_stripped.startswith("nan\n"):
        return False
    
    # 过滤填写说明/注释（Excel 末尾的说明行）
    comment_keywords = [
        "本表格用于记录",
        "填写说明",
        "请按以下格式填写",
        "填写示例",
        "注意：此行",
        "请勿删除",
        "仅供参考"
    ]
    for keyword in comment_keywords:
        if keyword in content_stripped:
            return False
    
    # 内容太短（<20字符）不算有效答案
    if len(content_stripped) < 20:
        return False
    
    # 包含"简短回答"关键词，是有效答案（优先级最高，放在最前面）
    if "**简短回答**" in content:
        return True
    
    # 纯标题（只有 #### 标题且没有其他内容）不算有效答案
    # 注意：如果包含简短回答，上面已经返回 True 了
    if content_stripped.startswith("####") and len(content_stripped) < 50:
        return False
    
    # 纯关键词列表不算有效答案
    if content_stripped.startswith("**关键词**"):
        return False
    
    # 标题结尾是问号的，通常是标题而非答案（但如果包含简短回答，上面已经返回 True）
    if content_stripped.endswith("？") or content_stripped.endswith("?"):
        return False
    
    # 特征描述不算有效答案
    if "**二维码特征**" in content:
        return False
    
    # 包含完整指引内容
    if "找到二维码" in content:
        return True
    
    # 扫码位置指引，但需要包含具体位置且不是特征描述
    if "**扫码位置**" in content and len(content_stripped) > 25:
        return True
    
    # 包含具体信息的片段（如时间、费用、步骤等）
    # 这些片段通常是答案的一部分，应该被接受
    info_patterns = [
        r'\d+[-~]\d+小时',  # 时间范围：4-8小时
        r'\d+[-~]\d+分钟',  # 时间范围：30-60分钟
        r'\d+\.?\d*元',    # 费用：1.5元
        r'元/度',          # 单价
        r'按.*计费',       # 计费方式
        r'^\d+\.',         # 编号列表：1. xxx
        r'^-\s+\*\*',      # 列表项：- **xxx**
        r'\*\*.*\*\*：',   # 加粗标签：**xxx**：
    ]
    for pattern in info_patterns:
        if re.search(pattern, content_stripped):
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
    top_k: int = 5,
    table_names: Optional[List[str]] = None
) -> Optional[Any]:
    """
    执行单次知识库搜索
    """
    try:
        search_response = knowledge_client.search(
            query=query,
            top_k=top_k,
            min_score=min_score,
            table_names=table_names  # 指定数据集，None 表示搜索所有
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
    retry_delay: float = 1.0,
    table_names: Optional[List[str]] = None
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
        table_names: 指定搜索的数据集列表
    
    Returns:
        (knowledge_chunks, knowledge_context, success, best_score)
    """
    knowledge_chunks: List[Dict[str, Any]] = []
    knowledge_context = ""
    best_score = 0.0  # 默认得分为 0
    
    # 生成增强查询列表
    enhanced_queries = _enhance_query(query)
    logger.info(f"搜索查询列表: {enhanced_queries}")
    
    all_results: List[Dict[str, Any]] = []
    
    # 执行多次搜索，收集结果
    for search_query in enhanced_queries[:3]:  # 最多使用3个查询变体
        for attempt in range(max_retries):
            response = _search_single_query(
                knowledge_client, search_query, min_score=0.4, top_k=10, table_names=table_names
            )
            
            if response and response.chunks:
                logger.info(f"搜索 '{search_query}' 返回 {len(response.chunks)} 条结果")
                for idx, c in enumerate(response.chunks):
                    logger.info(f"  结果[{idx}] 得分: {c.score:.3f}, 内容: {c.content[:60]}...")
                for chunk in response.chunks:
                    # 去重：如果已存在且新得分更高，则更新得分
                    chunk_id = chunk.chunk_id
                    existing = next((r for r in all_results if r.get("chunk_id") == chunk_id), None)
                    if existing:
                        # 如果新得分更高，更新得分
                        if chunk.score > existing["score"]:
                            existing["score"] = chunk.score
                            existing["query"] = search_query
                            logger.info(f"更新已有结果的得分: {chunk_id} -> {chunk.score:.3f}")
                    else:
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
        return knowledge_chunks, knowledge_context, True, 0.0
    
    # 按得分排序
    all_results.sort(key=lambda x: x["score"], reverse=True)
    
    # 收集多个有效答案（最多3个），而不是只取第一个
    valid_results = []
    invalid_results = []  # 记录被过滤的结果
    for result in all_results:
        if _is_valid_answer_content(result["content"]):
            valid_results.append(result)
            logger.info(f"找到有效答案[{len(valid_results)}]，得分: {result['score']:.2f}, 内容: {result['content'][:50]}...")
            if len(valid_results) >= 3:  # 最多取3个有效答案
                break
        else:
            invalid_results.append(result)
    
    # 如果没有找到有效答案，记录被过滤的内容
    if not valid_results and invalid_results:
        logger.warning(f"所有搜索结果都是无效内容（空片段/标题/nan），共 {len(invalid_results)} 条结果被过滤")
        for i, r in enumerate(invalid_results[:3]):  # 只记录前3条
            logger.info(f"被过滤内容[{i}]，得分: {r['score']:.2f}, 内容: {repr(r['content'][:100])}")
        
        # 尝试用标题内容再次搜索（解决标题和答案分片的问题）
        for r in invalid_results:
            content = r["content"].strip()
            # 如果是标题格式，提取标题内容再次搜索
            if content.startswith("#### ") and content.endswith("？"):
                title_content = content[5:].strip()  # 去掉 "#### " 前缀
                logger.info(f"检测到标题片段，尝试用标题内容再次搜索: {title_content}")
                
                # 用标题内容再次搜索
                retry_response = _search_single_query(knowledge_client, title_content, min_score=0.4, top_k=10, table_names=table_names)
                if retry_response and retry_response.chunks:
                    logger.info(f"标题重试搜索返回 {len(retry_response.chunks)} 条结果")
                    for chunk in retry_response.chunks:
                        is_valid = _is_valid_answer_content(chunk.content)
                        logger.info(f"标题重试结果，得分: {chunk.score:.2f}, 有效: {is_valid}, 内容: {chunk.content[:50]}...")
                        if is_valid:
                            logger.info(f"标题重试搜索成功！")
                            knowledge_chunks = [{
                                "content": chunk.content,
                                "score": chunk.score,
                                "doc_id": chunk.doc_id
                            }]
                            return knowledge_chunks, chunk.content, True, chunk.score
                else:
                    logger.info(f"标题重试搜索无结果")
        
        return knowledge_chunks, knowledge_context, True, 0.0
    
    # 构建知识库上下文（合并多个有效答案）
    knowledge_chunks = [{
        "content": r["content"],
        "score": r["score"],
        "doc_id": r["doc_id"]
    } for r in valid_results]
    
    # 合并多个答案的内容
    knowledge_context = "\n\n---\n\n".join([r["content"] for r in valid_results])
    best_score = valid_results[0]["score"]  # 最高得分
    
    # 如果得分太低（< 0.6），可能不够相关
    if best_score < 0.6:
        logger.warning(f"最佳结果得分较低 ({best_score:.2f})，可能不够相关")
    
    logger.info(f"最终传递给LLM的知识库内容: {len(valid_results)} 条有效答案，最高得分: {best_score:.2f}")
    
    return knowledge_chunks, knowledge_context, True, best_score


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
    
    # 优先使用改写后的搜索词，如果没有则使用原始消息
    search_query = state.rewritten_query if state.rewritten_query else state.user_message
    logger.info(f"知识库搜索词: {search_query} (原始: {state.user_message})")
    
    # 搜索知识库（带重试机制）
    knowledge_chunks, knowledge_context, kb_success, knowledge_score = _search_knowledge_with_retry(
        knowledge_client=knowledge_client,
        query=search_query,
        max_retries=3,
        retry_delay=1.0,
        table_names=KNOWLEDGE_TABLE_NAMES  # 使用新数据集
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
    
    # 如果知识库搜索失败（技术故障），使用降级方案
    if not kb_success:
        logger.warning("知识库搜索失败，使用降级方案")
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
    
    # 如果知识库无结果但搜索成功，使用配置文件中的SP（里面已有友好引导话术）
    # 此时 knowledge_context 为空，SP 中有"知识库无内容时引导用户"的规则
    if not knowledge_context:
        logger.info("知识库无结果，使用配置文件中的友好引导话术")
    
    # 记录知识库得分
    logger.info(f"知识库得分: {knowledge_score:.2f}, 内容长度: {len(knowledge_context)} 字符")
    
    # 渲染提示词
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({
        "user_message": state.user_message,
        "knowledge_context": knowledge_context,
        "knowledge_score": round(knowledge_score, 2) if knowledge_score else 0.0,
        "intent": state.intent
    })
    
    # 初始化 LLM 客户端
    llm_client = create_llm_client(ctx=ctx, provider="doubao")
    
    # 构建消息（使用对话历史作为上下文，让 AI 更有人情味！）
    messages = [SystemMessage(content=sp)]
    
    # 先添加对话历史（最近 10 轮，避免太长但又有上下文）
    if state.conversation_history:
        recent_history = state.conversation_history[-10:] if len(state.conversation_history) > 10 else state.conversation_history
        for msg in recent_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
    
    # 最后添加当前用户消息
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
1. 有帮助
2. 没有帮助"""
        reply_content_with_feedback = reply_content + feedback_prompt
        logger.info("已添加评价提示")
    else:
        reply_content_with_feedback = reply_content
        logger.info("不添加评价提示（LLM 判断不需要）")
    
    # 判断知识库是否缺失
    # 判断条件：
    # 1. knowledge_context 为空
    # 2. 或者 knowledge_chunks 为空
    # 3. 或者回复内容包含"没有资料"、"暂时无法"等关键词
    knowledge_missed = False
    
    if not knowledge_context or not knowledge_chunks:
        knowledge_missed = True
        logger.info("标记为知识库缺失：knowledge_context 或 knowledge_chunks 为空")
    else:
        # 检查回复内容是否包含"知识库没有覆盖"的关键词
        missing_keywords = ["没有资料", "暂时无法", "还在学习", "不好意思", "暂时没有"]
        for keyword in missing_keywords:
            if keyword in reply_content_with_feedback:
                knowledge_missed = True
                logger.info(f"标记为知识库缺失：回复包含关键词 '{keyword}'")
                break
    
    return KnowledgeQAOutput(
        reply_content=reply_content_with_feedback,
        knowledge_chunks=knowledge_chunks,
        need_feedback=should_ask_feedback,
        knowledge_missed=knowledge_missed
    )
