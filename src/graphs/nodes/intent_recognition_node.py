"""
意图识别节点 - 判断用户问题的类型
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
    desc: 分析用户消息，判断问题类型（使用指导/故障处理/投诉兜底/评价反馈）
    integrations: 大语言模型
    """
    # 获取上下文
    ctx = runtime.context
    
    user_message = state.user_message.strip()
    
    # 优先判断是否为评价反馈
    # 用户回复 "1" 或 "2" 表示评价
    if user_message == "1" or user_message == "【1】":
        return IntentRecognitionOutput(intent="feedback_good")
    if user_message == "2" or user_message == "【2】":
        return IntentRecognitionOutput(intent="feedback_bad")
    # 也支持文字形式评价
    if user_message in ["很好", "满意", "有帮助"]:
        return IntentRecognitionOutput(intent="feedback_good")
    if user_message in ["没有帮助", "不满意", "没用"]:
        return IntentRecognitionOutput(intent="feedback_bad")
    
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
    if "使用指导" in intent_text or "扫码" in intent_text:
        intent = "usage_guidance"
    elif "故障处理" in intent_text or "充电" in intent_text or "拔不" in intent_text:
        intent = "fault_handling"
    elif "投诉" in intent_text or "退款" in intent_text or "计费" in intent_text:
        intent = "complaint"
    
    return IntentRecognitionOutput(intent=intent)
