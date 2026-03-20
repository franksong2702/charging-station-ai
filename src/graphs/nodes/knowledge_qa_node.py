"""
知识库问答节点 - 基于知识库回答用户问题
"""
import os
import json
from typing import List, Dict, Any

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import KnowledgeClient, LLMClient, Config
from langchain_core.messages import SystemMessage, HumanMessage
from jinja2 import Template

from graphs.state import KnowledgeQAInput, KnowledgeQAOutput


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
    
    # 搜索知识库
    search_response = knowledge_client.search(
        query=state.user_message,
        top_k=5,
        min_score=0.5
    )
    
    # 提取知识库内容
    knowledge_chunks = []
    knowledge_context = ""
    
    if search_response.code == 0 and search_response.chunks:
        for chunk in search_response.chunks:
            chunk_dict = {
                "content": chunk.content,
                "score": chunk.score,
                "doc_id": chunk.doc_id
            }
            knowledge_chunks.append(chunk_dict)
            knowledge_context += f"\n{chunk.content}\n"
    
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
    
    # 渲染提示词
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({
        "user_message": state.user_message,
        "knowledge_context": knowledge_context,
        "intent": state.intent
    })
    
    # 初始化 LLM 客户端
    llm_client = LLMClient(ctx=ctx)
    
    # 构建消息
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]
    
    # 调用 LLM
    response = llm_client.invoke(
        messages=messages,
        model=llm_config.get("model", "doubao-seed-1-8-251228"),
        temperature=llm_config.get("temperature", 0.7),
        max_completion_tokens=llm_config.get("max_completion_tokens", 1000)
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
        reply_content = " ".join(text_parts).strip()
    else:
        reply_content = str(content).strip()
    
    return KnowledgeQAOutput(
        reply_content=reply_content,
        knowledge_chunks=knowledge_chunks
    )
