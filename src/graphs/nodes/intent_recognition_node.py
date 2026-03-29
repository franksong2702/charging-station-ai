"""
意图识别节点 - 判断用户问题的类型
支持：使用指导、故障处理、投诉兜底、转人工、不满意、评价反馈
"""
import os
import json
from typing import Dict, Any
from jinja2 import Template

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import SystemMessage, HumanMessage

from graphs.state import IntentRecognitionInput, IntentRecognitionOutput


def intent_recognition_node(
    state: IntentRecognitionInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> IntentRecognitionOutput:
    """
    title: 意图识别
    desc: 分析用户消息，判断问题类型（使用指导/故障处理/投诉兜底/转人工/不满意/评价反馈）
    integrations: 大语言模型
    """
    # 获取上下文
    ctx = runtime.context
    
    user_message = state.user_message.strip()
    
    # ==================== 优先判断特殊意图 ====================
    
    # 1. 评价反馈（支持半角/全角）
    if user_message in ["1", "１", "【1】", "【１】"]:
        return IntentRecognitionOutput(intent="feedback_good")
    if user_message in ["2", "２", "【2】", "【２】"]:
        return IntentRecognitionOutput(intent="feedback_bad")
    # 文字形式评价
    if user_message in ["很好", "满意", "有帮助"]:
        return IntentRecognitionOutput(intent="feedback_good")
    if user_message in ["没有帮助", "不满意", "没用"]:
        return IntentRecognitionOutput(intent="feedback_bad")
    
    # 2. 转人工（关键词匹配，优先级最高）
    transfer_keywords = ["转人工", "人工客服", "转接人工", "接人工", "人工服务", "转客服"]
    for keyword in transfer_keywords:
        if keyword in user_message:
            return IntentRecognitionOutput(intent="transfer_human")
    
    # 3. 不满意（用户表达不满）
    dissatisfied_keywords = ["没用", "不行", "还是不行", "没帮助", "太差了", "不好用", 
                            "没解决", "帮不了", "什么破", "垃圾", "投诉你"]
    for keyword in dissatisfied_keywords:
        if keyword in user_message:
            return IntentRecognitionOutput(intent="dissatisfied")
    
    # ==================== 调用 LLM 判断复杂意图 ====================
    
    # 读取配置文件
    cfg_file = os.path.join(
        os.getenv("COZE_WORKSPACE_PATH", ""),
        config.get("configurable", {}).get("llm_cfg", "config/intent_recognition_llm_cfg.json")
    )
    
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)
    
    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")
    
    # 使用 Jinja2 渲染用户提示词
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({"user_message": state.user_message})
    
    # 初始化 LLM 客户端
    client = LLMClient(ctx=ctx)
    
    # 构建消息
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]
    
    # 调用 LLM
    response = client.invoke(
        messages=messages,
        model=llm_config.get("model", "doubao-seed-1-8-251228"),
        temperature=llm_config.get("temperature", 0.3),
        max_completion_tokens=llm_config.get("max_completion_tokens", 500)
    )
    
    # 解析意图
    content = response.content
    if isinstance(content, list):
        # 处理多模态返回
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif isinstance(item, str):
                text_parts.append(item)
        intent_text = " ".join(text_parts).strip()
    else:
        intent_text = str(content).strip()
    
    # 提取意图关键词
    intent = "usage_guidance"  # 默认值
    if "使用指导" in intent_text:
        intent = "usage_guidance"
    elif "故障处理" in intent_text:
        intent = "fault_handling"
    elif "投诉" in intent_text:
        intent = "complaint"
    elif "转人工" in intent_text:
        intent = "transfer_human"
    elif "不满意" in intent_text:
        intent = "dissatisfied"
    
    return IntentRecognitionOutput(intent=intent)
