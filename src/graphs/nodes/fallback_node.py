"""
兜底流程节点 - 处理需要人工介入的场景
支持多轮确认：收集信息 → 生成总结 → 用户确认 → 创建工单
"""
import os
import json
import logging
import re
from jinja2 import Template

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import SystemMessage, HumanMessage

from graphs.state import FallbackInput, FallbackOutput

# 配置日志
logger = logging.getLogger(__name__)


def _extract_info_by_llm(
    ctx,
    user_message: str
) -> dict:
    """
    使用 LLM 从文本中提取手机号和车牌号
    
    Args:
        ctx: 上下文
        user_message: 用户消息
        
    Returns:
        {"phone": "手机号", "license_plate": "车牌号"}
    """
    prompt = f"""请从用户消息中提取手机号和车牌号信息。

用户消息：{user_message}

提取规则：
1. 手机号：11位数字，以1开头。用户可能用各种格式输入（带横线、空格等），请提取并标准化为纯数字。
2. 车牌号：省份简称+字母+5-6位字母或数字。用户可能中间有空格，请提取并标准化为无空格格式。
3. 如果某项信息不存在，返回空字符串。

请直接返回JSON格式，不要其他说明：
{{"phone": "手机号", "license_plate": "车牌号"}}"""

    client = LLMClient(ctx=ctx)
    response = client.invoke(
        messages=[HumanMessage(content=prompt)],
        model="doubao-seed-1-8-251228",
        temperature=0.1,  # 低温度，更确定性的输出
        max_completion_tokens=100
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
        content = " ".join(text_parts).strip()
    else:
        content = str(content).strip()
    
    # 解析 JSON
    try:
        # 清理可能的 markdown 代码块
        json_str = content.strip()
        if json_str.startswith("```"):
            json_str = re.sub(r'^```json?\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)
        
        result = json.loads(json_str)
        
        phone = str(result.get("phone", "")).strip()
        license_plate = str(result.get("license_plate", "")).strip()
        
        # 验证手机号格式
        if phone and len(re.sub(r'\D', '', phone)) == 11:
            phone = re.sub(r'\D', '', phone)  # 只保留数字
        else:
            phone = ""
        
        # 验证车牌号格式（简单校验）
        if license_plate and len(license_plate.replace(" ", "")) >= 7:
            license_plate = license_plate.replace(" ", "").upper()
        else:
            license_plate = ""
        
        logger.info(f"LLM 提取结果 - 手机号: {phone}, 车牌号: {license_plate}")
        return {"phone": phone, "license_plate": license_plate}
        
    except json.JSONDecodeError as e:
        logger.warning(f"LLM 返回 JSON 解析失败: {e}, 原始内容: {content}")
        return {"phone": "", "license_plate": ""}


def _generate_problem_summary(
    ctx,
    conversation_history: list,
    user_supplement: str
) -> str:
    """使用 LLM 从对话历史生成问题总结"""
    
    if not conversation_history:
        return "用户遇到充电桩相关问题，需要人工处理。"
    
    # 构建对话摘要
    dialogue_text = ""
    for msg in conversation_history[-10:]:  # 最近10轮对话
        role = "用户" if msg.get("role") == "user" else "客服"
        content = msg.get("content", "")
        dialogue_text += f"{role}：{content}\n"
    
    # 使用 LLM 生成总结
    prompt = f"""请根据以下对话记录，总结用户遇到的问题。

对话记录：
{dialogue_text}

用户补充说明：{user_supplement if user_supplement else "无"}

请用简洁的语言总结：
1. 用户遇到的问题是什么
2. 尝试了哪些方法
3. 当前状态如何

总结（不超过100字）："""

    client = LLMClient(ctx=ctx)
    response = client.invoke(
        messages=[HumanMessage(content=prompt)],
        model="doubao-seed-1-8-251228",
        temperature=0.3,
        max_completion_tokens=200
    )
    
    if isinstance(response.content, list):
        text_parts = []
        for item in response.content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return " ".join(text_parts).strip()
    return str(response.content).strip()


def fallback_node(
    state: FallbackInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> FallbackOutput:
    """
    title: 兜底流程处理
    desc: 处理需要人工介入的场景，收集信息并生成问题总结让用户确认
    integrations: 大语言模型
    """
    ctx = runtime.context
    user_message = state.user_message.strip()
    phase = state.fallback_phase or "collect_info"
    
    logger.info(f"兜底流程 - 当前阶段: {phase}, 用户消息: {user_message}")
    
    # ==================== 取消机制 ====================
    # 用户可以在任何阶段取消兜底流程
    cancel_keywords = ["取消", "不用了", "算了", "不需要了", "不用管了", "没事了", "不要了", "不麻烦了"]
    # 使用模糊匹配，检测用户是否想取消
    for keyword in cancel_keywords:
        if keyword in user_message:
            logger.info(f"兜底流程 - 用户取消（关键词: {keyword}）")
            return FallbackOutput(
                reply_content="好的，已取消。如果您还有其他问题，欢迎随时问我～",
                fallback_phase="",  # 清空状态，退出兜底流程
                phone="",
                license_plate="",
                problem_summary="",
                user_supplement="",
                case_confirmed=False
            )
    
    # ==================== 阶段1：收集信息 ====================
    if phase == "collect_info":
        phone = state.phone
        license_plate = state.license_plate
        
        # 使用 LLM 从用户消息中提取信息
        extracted = _extract_info_by_llm(ctx, user_message)
        extracted_phone = extracted.get("phone", "")
        extracted_plate = extracted.get("license_plate", "")
        
        if extracted_phone:
            phone = extracted_phone
        if extracted_plate:
            license_plate = extracted_plate
        
        # 检查是否已收集齐信息
        if phone and license_plate:
            # 信息齐全，生成问题总结
            problem_summary = _generate_problem_summary(ctx, state.conversation_history, "")
            logger.info(f"兜底流程 - 信息收集完成，生成问题总结: {problem_summary[:50]}...")
            
            reply_content = f"""感谢您的配合，我已记录以下信息：

📱 手机号：{phone}
🚗 车牌号：{license_plate}

───────────
**问题总结：**
{problem_summary}

───────────
请问以上信息是否准确？如有需要补充，请直接告诉我；如确认无误，请回复"确认"。"""
            
            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase="confirm",
                phone=phone,
                license_plate=license_plate,
                problem_summary=problem_summary,
                user_supplement="",
                case_confirmed=False
            )
        
        # 信息不齐全，继续收集
        if not phone and not license_plate:
            reply_content = """好的，我们会将您的问题记录下来，并反馈给相关工作人员处理。

为了方便工作人员联系您，请提供以下信息：

📱 请提供您的手机号：
🚗 请提供您的车牌号：

您可以直接回复，例如："手机13812345678，车牌京A12345" """
        
        elif not phone:
            reply_content = f"""已记录车牌号：{license_plate}

📱 请提供您的手机号："""
        
        else:
            reply_content = f"""已记录手机号：{phone}

🚗 请提供您的车牌号："""
        
        return FallbackOutput(
            reply_content=reply_content,
            fallback_phase="collect_info",
            phone=phone,
            license_plate=license_plate,
            problem_summary="",
            user_supplement="",
            case_confirmed=False
        )
    
    # ==================== 阶段2：用户确认 ====================
    elif phase == "confirm":
        phone = state.phone
        license_plate = state.license_plate
        problem_summary = state.problem_summary
        user_supplement = state.user_supplement
        
        # 检查用户是否确认
        if user_message in ["确认", "确认无误", "没问题", "是的", "对", "好的"]:
            logger.info(f"兜底流程 - 用户确认完成")
            
            # 整合用户补充内容
            final_summary = problem_summary
            if user_supplement:
                final_summary = f"{problem_summary}\n\n用户补充：{user_supplement}"
            
            reply_content = """感谢您的确认！

我们已将您的问题记录下来，相关工作人员会在24小时内联系您处理。

如有其他问题，随时可以问我。"""
            
            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase="done",
                phone=phone,
                license_plate=license_plate,
                problem_summary=final_summary,
                user_supplement=user_supplement,
                case_confirmed=True
            )
        
        # 用户有补充内容
        logger.info(f"兜底流程 - 用户补充: {user_message}")
        user_supplement = f"{user_supplement}\n{user_message}" if user_supplement else user_message
        
        # 重新生成问题总结
        new_summary = _generate_problem_summary(ctx, state.conversation_history, user_supplement)
        
        reply_content = f"""已补充您的说明，更新后的问题总结：

───────────
**问题总结：**
{new_summary}

───────────
请问以上信息是否准确？如有需要继续补充，请直接告诉我；如确认无误，请回复"确认"。"""
        
        return FallbackOutput(
            reply_content=reply_content,
            fallback_phase="confirm",
            phone=phone,
            license_plate=license_plate,
            problem_summary=new_summary,
            user_supplement=user_supplement,
            case_confirmed=False
        )
    
    # ==================== 阶段3：已完成 ====================
    elif phase == "done":
        return FallbackOutput(
            reply_content="您的问题已提交，工作人员会尽快联系您。",
            fallback_phase="done",
            phone=state.phone,
            license_plate=state.license_plate,
            problem_summary=state.problem_summary,
            user_supplement=state.user_supplement,
            case_confirmed=True
        )
    
    # 默认返回
    return FallbackOutput(
        reply_content="抱歉，处理出现异常，请稍后重试。",
        fallback_phase="collect_info",
        phone="",
        license_plate="",
        problem_summary="",
        user_supplement="",
        case_confirmed=False
    )
