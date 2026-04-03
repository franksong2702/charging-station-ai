"""
意图识别节点 - 使用 LLM 智能判断用户意图
支持：使用指导、故障处理、投诉兜底、轻度不满、满意、评价反馈
"""
import os
import re
import json
import logging
from typing import Dict, Any
from jinja2 import Template

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import SystemMessage, HumanMessage

from graphs.state import IntentRecognitionInput, IntentRecognitionOutput

# 配置日志
logger = logging.getLogger(__name__)


def intent_recognition_node(
    state: IntentRecognitionInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> IntentRecognitionOutput:
    """
    title: 意图识别
    desc: 使用 LLM 分析用户消息，判断问题类型
    integrations: 大语言模型
    """
    # 获取上下文
    ctx = runtime.context
    
    user_message = state.user_message.strip()
    
    # ==================== 快速判断：评价反馈（数字） ====================
    # 数字评价优先处理，不需要调用 LLM
    if user_message in ["1", "１", "【1】", "【１】"]:
        return IntentRecognitionOutput(intent="feedback_good")
    if user_message in ["2", "２", "【2】", "【２】"]:
        return IntentRecognitionOutput(intent="feedback_bad")
    
    # ==================== 构建上下文信息 ====================
    # 构建兜底流程上下文，让 LLM 理解当前状态
    fallback_context = ""
    if state.fallback_phase:
        fallback_context = f"""
【当前处于兜底流程中】
- 阶段：{state.fallback_phase}
- 问题总结：{state.problem_summary or '暂无'}
- 问题描述：{state.entry_problem or '暂无'}
"""
    
    # ==================== 调用 LLM 判断意图 ====================
    
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
    user_prompt_content = up_tpl.render({
        "user_message": user_message,
        "fallback_context": fallback_context
    })
    
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
        max_completion_tokens=llm_config.get("max_completion_tokens", 100)
    )
    
    # 解析意图
    content = response.content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif isinstance(item, str):
                text_parts.append(item)
        intent_text = " ".join(text_parts).strip()
    else:
        intent_text = str(content).strip()
    
    # 映射意图关键词到标准意图
    logger.info(f"LLM 返回意图文本: {intent_text}, 当前兜底阶段: {state.fallback_phase}")
    
    intent = "usage_guidance"  # 默认值
    
    # 【重要】必须先判断"退出兜底"，再判断"兜底"，否则"退出兜底"会被错误匹配为"兜底"
    if "问候" in intent_text or "你好" in intent_text:
        # 问候语归为使用指导类，引导用户提问
        intent = "usage_guidance"
    elif "闲聊" in intent_text:
        # 闲聊也归为使用指导类，让知识库问答节点友好地引导用户
        intent = "usage_guidance"
    elif "使用指导" in intent_text:
        intent = "usage_guidance"
    elif "故障处理" in intent_text:
        intent = "fault_handling"
    elif "退出兜底" in intent_text or "取消兜底" in intent_text:
        # 优先判断退出兜底
        intent = "exit_fallback"
    elif "继续兜底" in intent_text or "补充信息" in intent_text:
        intent = "fallback"
    elif "投诉兜底" in intent_text or "投诉" in intent_text:
        intent = "fallback"
    elif "兜底" in intent_text or "强烈不满" in intent_text:
        intent = "fallback"
    elif "不满意" in intent_text:
        intent = "dissatisfied"
    elif "满意" in intent_text:
        intent = "satisfied"
    elif "好评" in intent_text or "有帮助" in intent_text:
        intent = "feedback_good"
    elif "差评" in intent_text or "没帮助" in intent_text:
        intent = "feedback_bad"
    
    # 【关键逻辑】在兜底流程中，问新问题应该退出兜底
    if state.fallback_phase:
        if intent in ["usage_guidance", "fault_handling"]:
            # 用户在兜底流程中问使用问题或故障问题，应该退出兜底
            intent = "exit_fallback"
    
    return IntentRecognitionOutput(intent=intent)
