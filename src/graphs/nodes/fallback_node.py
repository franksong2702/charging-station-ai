"""
兜底流程节点 - 处理需要人工介入的场景

核心原则：
1. 态度与澄清原则：先安抚，问清楚问题，尽量挡投诉
2. 总结与确认原则：进入兜底后先总结问题，再收集手机号和车牌号

优化点：
1. 新增"澄清安抚"阶段（clarify）：先问清楚问题，安抚情绪
2. 新增"总结与收集"阶段（summary_collect）：先总结问题，再收集联系信息
3. 用户说什么就记什么，要改什么就改什么，最后确认
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

from graphs.state import FallbackInput, FallbackOutput

# 配置日志
logger = logging.getLogger(__name__)


def _extract_info_by_llm(
    ctx,
    user_message: str,
    check_complaint: bool = False
) -> dict:
    """
    使用 LLM 从文本中提取手机号、车牌号和问题描述
    
    Args:
        ctx: 上下文
        user_message: 用户消息
        check_complaint: 是否检查用户是否在抱怨
        
    Returns:
        {"phone": "手机号", "license_plate": "车牌号", "problem": "问题描述", "is_complaint": bool, "complaint_reason": str}
    """
    try:
        prompt = f"""请从用户消息中提取信息。

用户消息：{user_message}

【提取规则】
1. 手机号：11位数字，以1开头
   - 用户可能分段说出：如"139。16425678"或"139 1642 5678"
   - 请将所有数字拼接起来，提取完整的11位手机号
   
2. 车牌号：省份简称+字母+5-6位字母或数字
   - 用户可能分段说出：如"沪a Dr 3509"或"沪 A 1 2 3 4 5"
   - 请将所有部分拼接，提取完整车牌号
   - 转为大写，去掉空格
   
3. 问题描述：用户描述的具体问题
   - 例如："充电桩坏了"、"优惠券没用"、"扣费错误"等
   - 如果用户只是确认或纠正，不需要提取问题描述

4. 抱怨判断：判断用户是否在抱怨或不满（仅当check_complaint=true时）
   - 例如："刚才不是说了吗"、"不是已经告诉过了"、"不要再问了"等

【输出格式】
请返回JSON格式：
{{"phone": "手机号", "license_plate": "车牌号", "problem": "问题描述", "is_complaint": true/false, "complaint_reason": "如果抱怨，说明原因"}}

如果某项信息不存在或不需要提取，返回空字符串""。

请直接返回JSON格式，不要其他说明："""

        client = create_llm_client(ctx=ctx, provider="doubao")
        response = client.invoke(
            messages=[HumanMessage(content=prompt)],
            model="doubao-seed-1-8-251228",
            temperature=0.1,
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
        
        # 清理可能的 markdown 代码块
        json_str = content.strip()
        if json_str.startswith("```"):
            json_str = re.sub(r'^```json?\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)
        
        result = json.loads(json_str)
        
        phone = str(result.get("phone", "")).strip()
        license_plate = str(result.get("license_plate", "")).strip()
        problem = str(result.get("problem", "")).strip()
        
        # 手机号不验证格式，用户输入什么就接受什么，让用户确认即可
        if phone:
            phone = re.sub(r'\D', '', phone)
        
        # 车牌号不验证格式，只要用户提供就记录，让用户确认即可
        if license_plate:
            license_plate = license_plate.replace(" ", "").upper()
        else:
            license_plate = ""
        
        # 如果需要检查抱怨，提取抱怨信息
        is_complaint = result.get("is_complaint", False)
        complaint_reason = result.get("complaint_reason", "")
        
        logger.info(f"LLM 提取结果 - 手机号: {phone}, 车牌号: {license_plate}, 问题: {problem[:30] if problem else ''}, 抱怨: {is_complaint}")
        return {
            "phone": phone, 
            "license_plate": license_plate,
            "problem": problem,
            "is_complaint": is_complaint,
            "complaint_reason": complaint_reason
        }
        
    except Exception as e:
        logger.error(f"LLM 提取信息失败: {e}")
        return {
            "phone": "",
            "license_plate": "",
            "problem": "",
            "is_complaint": False,
            "complaint_reason": ""
        }


def _is_confirm(user_message: str) -> bool:
    """判断用户是否在确认"""
    # 确认关键词（去掉标点后匹配）
    confirm_keywords = [
        "确认", "确认无误", "没问题", "是的", "对的", "好的", "行", "可以", "嗯嗯",
        "准确", "没错", "对了", "正确", "ok", "okay", "收到"
    ]
    msg = re.sub(r'[，。！？、\.\,\!\?\~\s]', '', user_message.lower())
    for kw in confirm_keywords:
        if kw in msg:
            return True
    return False


def _is_cancel(user_message: str) -> bool:
    """判断用户是否要取消"""
    cancel_keywords = ["取消", "算了", "不要了", "不用处理", "不需要", "不聊了", "再见"]
    msg = user_message.lower()
    for kw in cancel_keywords:
        if kw in msg:
            return True
    return False


def fallback_node(
    state: FallbackInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> FallbackOutput:
    """
    title: 兜底流程处理
    desc: 先澄清安抚，再总结与确认：用户说什么就记什么，要改什么就改什么，最后确认
    integrations: 大语言模型
    """
    ctx = runtime.context
    user_message = state.user_message.strip()
    phase = state.fallback_phase or "clarify"
    
    logger.info(f"兜底流程 - 当前阶段: {phase}, 用户消息: {user_message}")
    
    # 初始化状态
    phone = state.phone
    license_plate = state.license_plate
    problem_summary = state.problem_summary
    entry_problem = state.entry_problem
    
    # 记录对话截断索引
    conversation_truncate_index = state.conversation_truncate_index
    if conversation_truncate_index is None:
        conversation_truncate_index = len(state.conversation_history) if state.conversation_history else 0
        logger.info(f"兜底流程 - 记录对话截断索引: {conversation_truncate_index}")
    
    # ==================== 取消机制 ====================
    if _is_cancel(user_message):
        logger.info("兜底流程 - 用户取消")
        return FallbackOutput(
            reply_content="好的，已取消。如果您还有其他问题，欢迎随时问我～",
            fallback_phase="",
            phone="",
            license_plate="",
            problem_summary="",
            user_supplement="",
            entry_problem="",
            case_confirmed=False,
            conversation_truncate_index=conversation_truncate_index
        )
    
    # ==================== 澄清安抚阶段（先搞清楚问题，安抚情绪） ====================
    if phase == "clarify":
        # 先看有没有已经保存的问题（保留之前用户说的）
        if not problem_summary and not entry_problem:
            # 没有保存过问题，提取用户消息中的信息
            extracted = _extract_info_by_llm(ctx, user_message, check_complaint=True)
            extracted_problem = extracted.get("problem", "")
            
            # 更新问题（如果有新的问题描述）
            if extracted_problem and not problem_summary:
                problem_summary = extracted_problem
        else:
            # 已有保存的问题，不用再提取了
            extracted_problem = problem_summary or entry_problem
        
        # 如果用户已经说了问题，先总结一下，问他是否确定要走兜底流程
        if problem_summary or entry_problem:
            current_problem = problem_summary or entry_problem
            reply_content = f"""哦，那我明白了，您的问题大概是这样的：{current_problem}

您的问题我们会反馈给专业的客服团队去处理。请您留下手机号和车牌号，方便我们的客服后续联系您。"""
            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase="summary_collect",
                phone=phone,
                license_plate=license_plate,
                problem_summary=current_problem,
                user_supplement="",
                entry_problem=current_problem,
                case_confirmed=False,
                conversation_truncate_index=conversation_truncate_index
            )
        
        # 用户还没说清楚问题，先安抚并引导
        reply_content = """非常抱歉给您带来了不好的体验！

您能跟我说说具体遇到了什么情况吗？我先帮您看看～"""
        
        return FallbackOutput(
            reply_content=reply_content,
            fallback_phase="clarify",
            phone=phone,
            license_plate=license_plate,
            problem_summary=problem_summary,
            user_supplement="",
            entry_problem=entry_problem,
            case_confirmed=False,
            conversation_truncate_index=conversation_truncate_index
        )
    
    # ==================== 总结与收集阶段（收集手机号和车牌号） ====================
    if phase == "summary_collect" or phase == "collect_info" or phase == "" or phase == "ask_problem":
        # 提取用户消息中的信息
        extracted = _extract_info_by_llm(ctx, user_message, check_complaint=False)
        extracted_phone = extracted.get("phone", "")
        extracted_plate = extracted.get("license_plate", "")
        extracted_problem = extracted.get("problem", "")
        
        # 更新信息
        updated = []
        if extracted_phone:
            phone = extracted_phone
            updated.append(f"手机号 {phone}")
        if extracted_plate:
            license_plate = extracted_plate
            updated.append(f"车牌号 {license_plate}")
        if extracted_problem:
            # 只有当用户明确说了新的问题时才更新，否则保留之前的
            problem_summary = extracted_problem
            updated.append(f"情况 {problem_summary}")
        
        # 检查是否有信息更新
        if updated:
            logger.info(f"兜底流程 - 更新信息: {', '.join(updated)}")
        else:
            logger.info("兜底流程 - 未提取到新信息，继续询问")
        
        # 检查是否需要让用户确认（已收集到手机号和车牌号）
        if phone and license_plate:
            # 信息齐全，让用户确认
            reply_content = f"""好的，已记录：

📱 手机号：{phone}
🚗 车牌号：{license_plate}
📝 情况：{problem_summary}

───────────
以上信息准确吗？准确的话回复"确认"，有误的话请告诉我～"""
            
            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase="confirm",
                phone=phone,
                license_plate=license_plate,
                problem_summary=problem_summary,
                user_supplement="",
                entry_problem=entry_problem,
                case_confirmed=False,
                conversation_truncate_index=conversation_truncate_index
            )
        
        # 信息不齐全，继续收集
        missing = []
        if not phone:
            missing.append("手机号")
        if not license_plate:
            missing.append("车牌号")
        
        # 已有部分信息，友好询问还缺什么
        missing_text = "、".join(missing)
        reply_content = f"""好的，{', '.join(updated) if updated else '收到'}～

还缺：{missing_text}

方便的话直接告诉我，比如："手机13812345678" 或 "车牌沪A12345" """
        
        return FallbackOutput(
            reply_content=reply_content,
            fallback_phase="summary_collect",
            phone=phone,
            license_plate=license_plate,
            problem_summary=problem_summary,
            user_supplement="",
            entry_problem=entry_problem,
            case_confirmed=False,
            conversation_truncate_index=conversation_truncate_index
        )
    
    # ==================== 确认阶段 ====================
    if phase == "confirm":
        # 用户说确认
        if _is_confirm(user_message):
            logger.info("兜底流程 - 用户确认完成")
            reply_content = """✅ 收到您的问题，我们的工作人员将会尽快处理，并在1-3个工作日内联系您。

如有其他问题，随时可以问我。"""
            
            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase="done",
                phone=phone,
                license_plate=license_plate,
                problem_summary=problem_summary,
                user_supplement="",
                entry_problem=entry_problem,
                case_confirmed=True,
                conversation_truncate_index=conversation_truncate_index
            )
        
        # 用户没有确认，继续收集/更新信息
        phase = "summary_collect"
    
    # ==================== 已完成阶段 ====================
    if phase == "done":
        return FallbackOutput(
            reply_content="您的问题已提交，工作人员会尽快联系您。",
            fallback_phase="done",
            phone=phone,
            license_plate=license_plate,
            problem_summary=problem_summary,
            user_supplement="",
            entry_problem=entry_problem,
            case_confirmed=True,
            conversation_truncate_index=conversation_truncate_index
        )
    
    # 默认处理
    return FallbackOutput(
        reply_content="收到～",
        fallback_phase=phase,
        phone=phone,
        license_plate=license_plate,
        problem_summary=problem_summary,
        user_supplement="",
        entry_problem=entry_problem,
        case_confirmed=False,
        conversation_truncate_index=conversation_truncate_index
    )
