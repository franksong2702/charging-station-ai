"""
意图识别节点 - 判断用户问题的类型
支持：使用指导、故障处理、投诉兜底、轻度不满、满意、评价反馈
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
    desc: 分析用户消息，判断问题类型。强烈不满/转人工走兜底，轻度不满继续尝试帮助
    integrations: 大语言模型
    """
    # 获取上下文
    ctx = runtime.context
    
    user_message = state.user_message.strip()
    
    # ==================== 检查是否在兜底流程中 ====================
    # 如果 fallback_phase 不为空，直接返回 fallback 意图继续兜底流程
    if state.fallback_phase:
        return IntentRecognitionOutput(intent="fallback")
    
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
    
    # 2. 强烈不满或转人工 → 走兜底流程
    # 强烈不满关键词（情绪激烈，需要人工介入）
    strong_dissatisfied_keywords = ["太差了", "垃圾", "投诉你", "什么破", "什么垃圾", 
                                    "要投诉", "强烈不满", "气死我了", "骗子", "坑人"]
    for keyword in strong_dissatisfied_keywords:
        if keyword in user_message:
            return IntentRecognitionOutput(intent="fallback")
    
    # 转人工 → 合并到兜底流程
    transfer_keywords = ["转人工", "人工客服", "转接人工", "接人工", "人工服务", "转客服"]
    for keyword in transfer_keywords:
        if keyword in user_message:
            return IntentRecognitionOutput(intent="fallback")
    
    # 3. 轻度不满 → AI 继续尝试帮助
    # 轻度不满关键词（可以尝试继续帮助）
    mild_dissatisfied_keywords = ["没用", "不行", "还是不行", "没帮助", "不好用", 
                                  "没解决", "帮不了", "还是不会", "搞不定"]
    for keyword in mild_dissatisfied_keywords:
        if keyword in user_message:
            return IntentRecognitionOutput(intent="dissatisfied")
    
    # 4. 满意（用户表达感谢）
    satisfied_keywords = ["谢谢", "感谢", "好的好的", "好的 谢谢", "谢谢你", "多谢", "谢谢啦"]
    for keyword in satisfied_keywords:
        if keyword in user_message:
            return IntentRecognitionOutput(intent="satisfied")
    
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
    elif "兜底" in intent_text or "强烈不满" in intent_text:
        intent = "fallback"
    elif "不满意" in intent_text:
        intent = "dissatisfied"
    elif "满意" in intent_text:
        intent = "satisfied"
    
    return IntentRecognitionOutput(intent=intent)
