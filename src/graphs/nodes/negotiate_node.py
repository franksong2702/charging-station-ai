"""
协商处理节点 - 简化版，先安抚情绪，再追问详情，最后给方案

核心原则：
1. 先检测情绪，情绪激动先安抚
2. 追问详情：什么问题、在哪里、什么时候、多少钱
3. 给方案，问用户是否接受
4. 用户拒绝或超过 5 轮 → 升级到兜底
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
    title: 协商处理 - 安抚情绪，追问详情，给方案
    desc: 先安抚情绪激动用户，再追问详情，根据常识给方案，用户拒绝时升级到兜底
    integrations: 大语言模型
    """
    ctx = runtime.context
    user_message = state.user_message.strip()
    conversation_history = state.conversation_history or []
    
    logger.info(f"协商处理 - 用户消息：{user_message}")
    
    # 获取当前轮数并 +1
    current_round = getattr(state, 'negotiate_round_count', 0) + 1
    
    # 检查是否超过最大轮数（5 轮）
    MAX_NEGOTIATE_ROUNDS = 5
    if current_round >= MAX_NEGOTIATE_ROUNDS:
        logger.info(f"协商轮数已达上限 ({MAX_NEGOTIATE_ROUNDS})，进入兜底流程")
        return NegotiateOutput(
            reply_content="好的，我理解您的需求了。为了进一步处理您的问题，请您提供手机号和车牌号，我帮您创建工单。",
            negotiate_phase="escalating",
            problem_understanding="",
            route_to_fallback=True
        )
    
    # 检查用户是否要求找人工客服
    if "人工" in user_message or "客服" in user_message and "找" in user_message:
        logger.info("用户要求找人工客服，进入兜底流程")
        return NegotiateOutput(
            reply_content="好的，我理解您的需求了。为了进一步处理您的问题，请您提供手机号和车牌号，我帮您创建工单。",
            negotiate_phase="escalating",
            problem_understanding="",
            route_to_fallback=True
        )
    
    # 检查用户是否明确拒绝方案
    if "不接受" in user_message or "不行" in user_message or "拒绝" in user_message:
        logger.info("用户明确拒绝方案，进入兜底流程")
        return NegotiateOutput(
            reply_content="好的，我理解您的需求了。为了进一步处理您的问题，请您提供手机号和车牌号，我帮您创建工单。",
            negotiate_phase="escalating",
            problem_understanding="",
            route_to_fallback=True
        )
    
    # 检测情绪
    is_angry = _detect_anger(user_message)
    
    # 第一轮：先安抚，再追问
    if current_round == 1:
        if is_angry:
            # 情绪激动：先安抚
            reply_content = "非常抱歉给您带来了这么糟糕的体验！我能理解您现在很生气。您能跟我说说具体发生了什么吗？"
        else:
            # 普通问题：简单询问
            reply_content = "非常抱歉给您带来了不便！请问您遇到了什么问题？"
        
        return NegotiateOutput(
            reply_content=reply_content,
            negotiate_phase="asking",
            problem_understanding="",
            route_to_fallback=False
        )
    
    # 后续轮次：追问详情，给方案
    # 构建上下文（最近 3 轮对话）
    recent_history = ""
    if conversation_history:
        for i, msg in enumerate(conversation_history[-6:], 1):  # 最近 3 轮（用户+AI 是 2 条）
            role = "用户" if i % 2 == 1 else "AI"
            recent_history += f"{role}: {msg.get('content', '')}\n"
    
    # 调用 LLM 生成追问和方案
    prompt = f"""你是一个专业的充电桩客服助手，擅长处理用户的退款、扣费、优惠券等问题。

【任务】
用户有退款/扣费/优惠券等问题，你需要：
1. 复述用户的问题（让用户感觉被理解）
2. 追问详细情况（如还需要了解什么）
3. 根据常识给初步解决方案
4. 问用户是否接受这个方案

【对话历史】
{recent_history if recent_history else "无历史对话"}

【当前用户消息】
{user_message}

【输出格式】
请返回 JSON 格式：
{{
    "understanding": "你理解的用户问题（详细，包含原因）",
    "question": "追问的问题（如'请问您使用的哪个平台的优惠券？'）",
    "solution": "初步解决方案（如'建议先在 App 里查看优惠券使用记录'）",
    "ask_accept": "是否询问接受（如'您看这样可以吗？'）"
}}

如果信息已经完整，可以不追问，直接给方案。

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
            max_completion_tokens=300
        )
        
        # 解析 LLM 返回
        content = str(response.content).strip()
        if content.startswith("```"):
            content = re.sub(r'^```json?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
        
        result = json.loads(content)
        
        understanding = result.get("understanding", "")
        question = result.get("question", "")
        solution = result.get("solution", "")
        ask_accept = result.get("ask_accept", "")
        
        # 生成回复
        reply_parts = []
        
        # 1. 复述理解（让用户感觉被理解）- 修复：将"用户"替换为"您"
        if understanding:
            understanding_for_user = understanding.replace("用户", "您")
            reply_parts.append(f"明白了，{understanding_for_user}。")
        
        # 2. 追问问题
        if question:
            reply_parts.append(question)
        
        # 3. 给方案
        if solution:
            reply_parts.append(f"建议：{solution}")
        
        # 4. 问是否接受
        if ask_accept:
            reply_parts.append(ask_accept)
        
        reply_content = "\n".join(reply_parts) if reply_parts else "好的，请问您具体遇到了什么情况？能详细说说吗？"
        
        logger.info(f"协商处理 - 回复：{reply_content}")
        
        return NegotiateOutput(
            reply_content=reply_content,
            negotiate_phase="asking",
            problem_understanding=understanding,
            route_to_fallback=False
        )
        
    except Exception as e:
        logger.error(f"协商处理失败：{e}")
        return NegotiateOutput(
            reply_content="好的，请问您具体遇到了什么情况？能详细说说吗？",
            negotiate_phase="asking",
            problem_understanding="",
            route_to_fallback=False
        )
