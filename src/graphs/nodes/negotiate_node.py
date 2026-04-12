"""
协商处理节点 - 使用 negotiate_round_count 判断轮数

核心原则：
1. 第 1-2 轮：追问详情（原因、平台、时间地点等）
2. 第 3 轮+：给出方案，询问是否接受
3. 用户接受方案 → 结束协商
4. 用户拒绝或超过 5 轮 → 升级到兜底
5. 用户提供手机号/车牌号/确认词 → 直接升级到兜底
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
    """判断用户是否表达了愤怒或强烈不满"""
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
    title: 协商处理 - 使用轮数计数器判断阶段
    desc: 根据 negotiate_round_count 判断轮数，1-2 轮追问，3 轮 + 给方案
    integrations: 大语言模型
    """
    ctx = runtime.context
    user_message = state.user_message.strip()
    conversation_history = state.conversation_history or []

    logger.info(f"协商处理 - 用户消息：{user_message}")

    # 获取当前协商轮数
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
    # 辅助判断函数
    # ============================================

    def _is_confirm_word(msg: str) -> bool:
        confirm_keywords = ["确认", "确认无误", "没问题", "是的", "对", "好的", "对呀", "是", "行", "嗯嗯"]
        msg_clean = re.sub(r'[，。！？、\.\,\!\?\~\s]', '', msg.lower())
        return any(keyword in msg_clean for keyword in confirm_keywords)

    def _has_phone_or_plate(msg: str) -> bool:
        has_phone = bool(re.search(r'1[3-9]\d{9}', msg))
        has_plate = bool(re.search(r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{4,5}[A-Z0-9 挂学警港澳]?', msg))
        return has_phone or has_plate

    def _is_reject_message(msg: str) -> bool:
        reject_keywords = ["不接受", "不行", "拒绝", "不同意", "不可以"]
        msg_clean = re.sub(r'[，。！？、\.\,\!\?\~\s]', '', msg.lower())
        return any(keyword in msg_clean for keyword in reject_keywords)

    # ============================================
    # 优先升级到 fallback 的情况
    # ============================================

    if _is_confirm_word(user_message):
        logger.info("用户说确认词，直接升级到兜底流程")
        return NegotiateOutput(
            reply_content="好的，我理解您的需求了。为了进一步处理您的问题，请您提供手机号和车牌号，我帮您创建工单。",
            negotiate_phase="escalating",
            problem_understanding="",
            route_to_fallback=True,
            negotiate_round_count=current_round
        )

    if _has_phone_or_plate(user_message):
        logger.info("用户提供手机号/车牌号，直接升级到兜底流程")
        return NegotiateOutput(
            reply_content="好的，我理解您的需求了。为了进一步处理您的问题，请您提供手机号和车牌号，我帮您创建工单。",
            negotiate_phase="escalating",
            problem_understanding="",
            route_to_fallback=True,
            negotiate_round_count=current_round
        )

    if _is_reject_message(user_message):
        logger.info("用户明确拒绝方案，进入兜底流程")
        return NegotiateOutput(
            reply_content="好的，我理解您的需求了。为了进一步处理您的问题，请您提供手机号和车牌号，我帮您创建工单。",
            negotiate_phase="escalating",
            problem_understanding="",
            route_to_fallback=True,
            negotiate_round_count=current_round
        )

    if "人工" in user_message or ("客服" in user_message and "找" in user_message):
        logger.info("用户要求找人工客服，进入兜底流程")
        return NegotiateOutput(
            reply_content="好的，我理解您的需求了。为了进一步处理您的问题，请您提供手机号和车牌号，我帮您创建工单。",
            negotiate_phase="escalating",
            problem_understanding="",
            route_to_fallback=True,
            negotiate_round_count=current_round
        )

    # ============================================
    # 正常协商处理流程 - 使用 negotiate_round_count 判断轮数
    # ============================================

    # 构建对话历史（仅用于上下文，不用于判断轮数）
    recent_history = ""
    if conversation_history:
        for i, msg in enumerate(conversation_history[-8:], 1):
            role = "用户" if i % 2 == 1 else "AI"
            recent_history += f"{role}: {msg.get('content', '')}\n"

    is_angry = _detect_anger(user_message)

    # 根据 negotiate_round_count 判断当前阶段
    if current_round <= 2:
        # 第 1-2 轮：追问详情
        stage = "追问详情"
        stage_instruction = """你现在是第 1-2 轮，任务是追问详情：
1. 如果用户情绪激动，先真诚安抚
2. 追问用户具体遇到了什么问题（原因、时间、地点、平台等）
3. 不要急着给方案，先了解清楚情况
4. 不要一上来就要手机号和车牌号"""
    else:
        # 第 3 轮+：给出方案
        stage = "给出方案"
        stage_instruction = """你现在是第 3 轮或更晚，任务是给出方案：
1. 复述并确认你理解的用户问题（让用户感觉被理解）
2. 根据充电桩客服常识给出初步解决方案
3. 问用户是否接受这个方案
4. 如果用户接受，可以说"好的，我帮您记录并提交"
5. 如果用户不接受，问用户具体哪里不满意"""

    prompt = f"""你是一个专业的充电桩客服助手，擅长处理用户的退款、扣费、优惠券等问题。

【当前阶段】{stage}
{stage_instruction}

【对话历史】
{recent_history if recent_history else "（第一轮对话）"}

【当前用户消息】
{user_message}

【用户情绪检测】
{'用户情绪激动，请先真诚安抚！' if is_angry else '用户情绪正常'}

【输出格式】
请返回 JSON 格式：
{{
    "understanding": "你理解的用户问题（详细，包含原因、时间、地点等）",
    "reply": "完整的回复内容"
}}

【重要】
- 第 1-2 轮不要急着给方案，先追问详情
- 第 3 轮+ 才给方案
- 不要一上来就要手机号和车牌号
- 不要提到"截图"、"凭证"、"照片"等系统不支持的内容
- 语言要简洁自然，像真人客服
- 直接返回 JSON 格式，不要其他说明："""

    try:
        client = create_llm_client(ctx=ctx, provider="doubao")
        response = client.invoke(
            messages=[HumanMessage(content=prompt)],
            model="doubao-seed-1-8-251228",
            temperature=0.3,
            max_completion_tokens=400
        )

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
