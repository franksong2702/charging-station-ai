"""
意图识别节点 - 使用 LLM 智能判断用户意图
支持：使用指导、故障处理、投诉兜底、轻度不满、满意、评价反馈

优化点：
1. 移除关键词匹配，改用 LLM 判断退出意图
2. 增强 LLM 提示词，让模型理解语义
3. 兜底流程中，只有明确退出意图才返回 exit_fallback
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
from tools.llm import create_llm_client
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
- 当前阶段：{state.fallback_phase}
- 问题总结：{state.problem_summary or '暂无'}
- 用户问题描述：{state.entry_problem or '暂无'}

【重要提示】
在兜底流程中，用户的回复可能有以下几种意图：
1. 确认问题总结，同意提交工单
2. 纠正或补充问题信息（如"你说得不对"、"我还要补充"）
3. 抱怨重复询问（如"刚才不是说了吗"）
4. 明确要退出兜底流程（如"算了不要了"、"取消"、"不需要了"）
5. 继续提问其他问题

【退出兜底判断规则】
- 只有用户明确、完全、肯定的退出意图才判断为"退出兜底"
- 如果用户说"取消"但上下文显示是在纠正问题，不是退出
- 如果用户说"算了"但后面跟着其他内容，需要看整体语义
- 如果用户只是抱怨或纠正，继续兜底流程
- 如果用户说"算了不处理了"、"取消处理"、"不需要人工"等，明确退出
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
    
    # 初始化 LLM 客户端（通过工厂创建，未来可轻松切换）
    client = create_llm_client(ctx=ctx, provider="doubao")
    
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
    
    # 【优化后的兜底退出判断 - 关键修复 P1】
    # 已在兜底流程中，只有明确退出才退出，否则强制保持为 fallback
    if state.fallback_phase:
        if intent == "exit_fallback":
            # LLM 已经判断为退出兜底，保持退出
            logger.info("意图识别 - LLM 判断退出兜底")
        else:
            # 【关键修复】其他任何意图（包括"故障处理"、"使用指导"等）都强制改为"fallback"
            # 因为用户已经在兜底流程中了，应该继续走完兜底流程，不要中途退出
            logger.info(f"意图识别 - 在兜底流程中，强制保持为 fallback，原意图: {intent}")
            intent = "fallback"
    
    return IntentRecognitionOutput(intent=intent)
