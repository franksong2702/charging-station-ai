"""
信息收集节点 - 收集用户投诉信息
"""
import os
import json
import re
from typing import Dict, Any

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import SystemMessage, HumanMessage
from jinja2 import Template

from graphs.state import InfoCollectionInput, InfoCollectionOutput


def info_collection_node(
    state: InfoCollectionInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> InfoCollectionOutput:
    """
    title: 信息收集
    desc: 从用户消息中提取关键信息（手机号、订单号、问题描述）
    integrations: 大语言模型
    """
    # 获取上下文
    ctx = runtime.context
    
    # 读取配置文件
    cfg_file = os.path.join(
        os.getenv("COZE_WORKSPACE_PATH", ""),
        config.get("configurable", {}).get("llm_cfg", "config/info_collection_llm_cfg.json")
    )
    
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)
    
    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")
    
    # 渲染提示词
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
    
    # 提取内容
    content = response.content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif isinstance(item, str):
                text_parts.append(item)
        response_text = " ".join(text_parts).strip()
    else:
        response_text = str(content).strip()
    
    # 解析用户信息（尝试提取JSON）
    user_info: Dict[str, str] = {}
    
    # 尝试从响应中提取手机号
    phone_pattern = r'1[3-9]\d{9}'
    phone_match = re.search(phone_pattern, state.user_message)
    if phone_match:
        user_info["phone"] = phone_match.group()
    
    # 尝试从响应中提取订单号（假设订单号格式为数字）
    order_pattern = r'订单[号]?[:：\s]*(\d+)'
    order_match = re.search(order_pattern, state.user_message)
    if order_match:
        user_info["order_id"] = order_match.group(1)
    
    # 尝试从响应中提取JSON
    try:
        # 查找JSON块
        json_pattern = r'\{[^{}]*\}'
        json_match = re.search(json_pattern, response_text)
        if json_match:
            json_str = json_match.group()
            extracted_info = json.loads(json_str)
            if isinstance(extracted_info, dict):
                user_info.update(extracted_info)
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # 确保有问题描述
    if "description" not in user_info:
        user_info["description"] = state.user_message
    
    # 生成回复
    reply_content = "感谢您的反馈！我们已收到您的问题，客服人员会在1个工作日内联系您处理。\n\n"
    if user_info.get("phone"):
        reply_content += f"📞 联系电话：{user_info.get('phone')}\n"
    if user_info.get("order_id"):
        reply_content += f"📋 订单号：{user_info.get('order_id')}\n"
    reply_content += f"\n📝 问题描述：{user_info.get('description', state.user_message)}"
    
    return InfoCollectionOutput(
        user_info=user_info,
        reply_content=reply_content
    )
