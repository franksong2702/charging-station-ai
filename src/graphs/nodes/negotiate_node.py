"""
协商处理节点 - 完全使用 LLM 提示词处理，不使用硬编码逻辑

核心原则：
1. 完全由提示词处理对话轮数判断
2. 第一轮：安抚 + 追问
3. 第二轮及以后：确认理解 + 给方案
4. 用户拒绝或超过 5 轮 → 升级到兜底
5. 用户提供手机号/车牌号/确认词 → 立即升级到兜底
"""
import os
import json
import logging
import re

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from tools.llm import create_llm_client
from langchain_core.messages import HumanMessage

from graphs.state import NegotiateInput, NegotiateOutput

logger = logging.getLogger(__name__)


def _detect_anger(user_message: str) -> bool:
    """
    判断用户是否表达了愤怒或强烈不满
    :param user_message: 用户消息
    :return: 是否愤怒
    """
    anger_keywords = [
        "什么破系统", "垃圾系统", "气死我了", "太差了", "什么垃圾", "破系统", 
        "烂系统", "什么东西", "太差劲", "太烂", "什么玩意儿", "破玩意儿",
        "垃圾", "太差", "气死", "太气人"
    ]
    msg = re.sub(r'[，。！？、\.\,\!\?\~\s]', '', user_message.lower())
    for keyword in anger_keywords:
        if keyword in msg:
            return True
    return False


def negotiate_node(
    state: NegotiateInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> NegotiateOutput:
    """
    title: 协商处理 - 完全由提示词处理轮数逻辑
    desc: 先安抚情绪激动用户，再根据对话历史判断轮数，第一轮追问，后续轮次给方案
    integrations: 大语言模型
    """
    ctx = runtime.context
    user_message = state.user_message.strip()
    conversation_history = state.conversation_history or []
    
    logger.info(f"协商处理 - 用户消息：{user_message}")
    
    # 获取当前轮数（用于最大轮数限制，不用于提示词逻辑）
    current_round = getattr(state, 'negotiate_round_count', 0) + 1
    
    # 检查是否超过最大轮数（5 轮）
    MAX_NEGOTIATE_ROUNDS = 5
    if current_round >= MAX_NEGOTIATE_ROUNDS:
        logger.info(f"协商轮数已达上限 ({MAX_NEGOTIATE_ROUNDS})，进入兜底流程")
        return NegotiateOutput(
            reply_content="好的，我理解您的需求了。为了进一步处理您的问题，请您提供手机号和车牌号，我帮您创建工单。",
            negotiate_phase="escalating",
            problem_understanding="",
            route_to_fallback=True,
            negotiate_round_count=current_round
        )
    
    # ============================================
    # 辅助判断函数（必须定义在使用之前）
    # ============================================
    
    # 检查用户是否在说确认词（这些应该在 fallback 中处理）
    def _is_confirm_word(msg: str) -> bool:
        confirm_keywords = ["确认", "确认无误", "没问题", "是的", "对", "好的", "对呀", "是", "行", "嗯嗯"]
        msg_clean = re.sub(r'[，。！？、\.\,\!\?\~\s]', '', msg.lower())
        return any(keyword in msg_clean for keyword in confirm_keywords)
    
    # 检查用户是否在提供手机号/车牌号
    def _has_phone_or_plate(msg: str) -> bool:
        has_phone = bool(re.search(r'1[3-9]\d{9}', msg))  # 手机号
        has_plate = bool(re.search(r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{4,5}[A-Z0-9挂学警港澳]?', msg))  # 车牌号
        return has_phone or has_plate
    
    # 检查用户是否明确拒绝方案
    def _is_reject_message(msg: str) -> bool:
        reject_keywords = ["不接受", "不行", "拒绝", "不同意", "不可以"]
        msg_clean = re.sub(r'[，。！？、\.\,\!\?\~\s]', '', msg.lower())
        return any(keyword in msg_clean for keyword in reject_keywords)
    
    # ============================================
    # 核心判断逻辑 - 优先升级到 fallback 的情况
    # ============================================
    
    # 1. 如果用户说确认词 → 直接升级到 fallback（这些应该在 fallback 中处理）
    if _is_confirm_word(user_message):
        logger.info("用户说确认词，直接升级到兜底流程")
        return NegotiateOutput(
            reply_content="好的，我理解您的需求了。为了进一步处理您的问题，请您提供手机号和车牌号，我帮您创建工单。",
            negotiate_phase="escalating",
            problem_understanding="",
            route_to_fallback=True,
            negotiate_round_count=current_round
        )
    
    # 2. 如果用户提供手机号/车牌号 → 直接升级到 fallback
    if _has_phone_or_plate(user_message):
        logger.info("用户提供手机号/车牌号，直接升级到兜底流程")
        return NegotiateOutput(
            reply_content="好的，我理解您的需求了。为了进一步处理您的问题，请您提供手机号和车牌号，我帮您创建工单。",
            negotiate_phase="escalating",
            problem_understanding="",
            route_to_fallback=True,
            negotiate_round_count=current_round
        )
    
    # 3. 如果用户明确拒绝 → 升级到 fallback
    if _is_reject_message(user_message):
        logger.info("用户明确拒绝方案，进入兜底流程")
        return NegotiateOutput(
            reply_content="好的，我理解您的需求了。为了进一步处理您的问题，请您提供手机号和车牌号，我帮您创建工单。",
            negotiate_phase="escalating",
            problem_understanding="",
            route_to_fallback=True,
            negotiate_round_count=current_round
        )
    
    # 4. 检查用户是否要求找人工客服
    if "人工" in user_message or "客服" in user_message and "找" in user_message:
        logger.info("用户要求找人工客服，进入兜底流程")
        return NegotiateOutput(
            reply_content="好的，我理解您的需求了。为了进一步处理您的问题，请您提供手机号和车牌号，我帮您创建工单。",
            negotiate_phase="escalating",
            problem_understanding="",
            route_to_fallback=True,
            negotiate_round_count=current_round
        )
    
    # ============================================
    # 其他情况 - 继续走正常的协商处理流程
    # ============================================
    
    # 构建对话历史上下文
    recent_history = ""
    if conversation_history:
        for i, msg in enumerate(conversation_history[-8:], 1):  # 最近 4 轮（用户+AI 是 2 条）
            role = "用户" if i % 2 == 1 else "AI"
            recent_history += f"{role}: {msg.get('content', '')}\n"
    
    # 检测情绪
    is_angry = _detect_anger(user_message)
    
    # 调用 LLM 生成回复 - 完全由提示词处理轮数逻辑
    prompt = f"""你是一个专业的充电桩客服助手，擅长处理用户的退款、扣费、优惠券等问题。

【核心规则】
通过对话历史的长度判断当前是第几轮：
- 如果对话历史为空或只有很少（不超过2条），说明是第一轮
- 如果对话历史超过2条，说明是第二轮及以后

【第一轮任务】
用户第一次找你，你需要：
1. 如果用户情绪激动，先真诚安抚
2. 再友好地追问用户具体遇到了什么问题

【第二轮及以后任务】
用户已经提供了一些信息，你需要：
1. 复述并确认你理解的用户问题（让用户感觉被理解）
2. 根据充电桩客服常识给出初步解决方案
3. 问用户是否接受这个方案

【对话历史】
{recent_history if recent_history else "（无历史对话，这是第一轮）"}

【当前用户消息】
{user_message}

【用户情绪检测】
{'用户情绪激动，请先真诚安抚！' if is_angry else '用户情绪正常'}

【输出格式】
请返回 JSON 格式：
{{
    "understanding": "你理解的用户问题（详细，包含原因）",
    "reply": "完整的回复内容（包含安抚/理解/方案/是否接受等所有内容）"
}}

【重要】
- 不要提到"截图"、"凭证"、"照片"等系统不支持的内容
- 语言要简洁，不要太啰嗦
- 直接返回 JSON 格式，不要其他说明："""

    try:
        client = create_llm_client(ctx=ctx, provider="doubao")
        response = client.invoke(
            messages=[HumanMessage(content=prompt)],
            model="doubao-seed-1-8-251228",
            temperature=0.3,
            max_completion_tokens=400
        )
        
        # 解析 LLM 返回
        content = str(response.content).strip()
        if content.startswith("```"):
            content = re.sub(r'^```json?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
        
        result = json.loads(content)
        
        understanding = result.get("understanding", "")
        reply_content = result.get("reply", "")
        
        if not reply_content:
            reply_content = "好的，请问您具体遇到了什么情况？能详细说说吗？"
        
        logger.info(f"协商处理 - 回复：{reply_content}")
        
        return NegotiateOutput(
            reply_content=reply_content,
            negotiate_phase="asking",
            problem_understanding=understanding,
            route_to_fallback=False,
            negotiate_round_count=current_round
        )
        
    except Exception as e:
        logger.error(f"协商处理失败：{e}")
        return NegotiateOutput(
            reply_content="好的，请问您具体遇到了什么情况？能详细说说吗？",
            negotiate_phase="asking",
            problem_understanding="",
            route_to_fallback=False,
            negotiate_round_count=current_round
        )
