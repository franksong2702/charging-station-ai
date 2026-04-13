"""
兜底流程节点 - 生产版本

核心原则：
1. 第 1-2 轮：追问详情（原因、平台、时间、地点等）
2. 第 3 轮+：收集手机号和车牌号
3. 信息完整后：生成总结，请求用户确认
4. 用户确认后：创建工单 + 发送邮件
"""
import os
import json
import logging
import re

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import FallbackInput, FallbackOutput

# 配置日志
logger = logging.getLogger(__name__)


def _is_confirm(user_message: str) -> bool:
    """判断用户是否在确认"""
    confirm_keywords = [
        "确认", "确认无误", "没问题", "是的", "对", "对的", "好的", "行", "可以", "可以的",
        "准确", "没错", "对了", "正确", "就是这样", "同意", "好", "嗯", "嗯嗯",
        "要得", "ok", "okay", "OK", "收到"
    ]
    msg = re.sub(r'[，。！？、\.\,\!\?\~\s]', '', user_message.lower())

    # 排除否定词
    if msg.startswith("不") and len(msg) > 1:
        rest = msg[1:]
        for keyword in confirm_keywords:
            if keyword in rest:
                return False

    for keyword in confirm_keywords:
        if keyword in msg:
            return True
    return False


def fallback_node(state: FallbackInput, config: RunnableConfig, runtime: Runtime[Context]) -> FallbackOutput:
    """
    title: 兜底流程处理 - 分阶段追问
    desc: 1-2 轮追问详情，3 轮 + 收集信息，确认后创建工单
    """
    ctx = runtime.context

    # 从状态中获取当前信息
    user_message = state.user_message.strip()
    fallback_round = getattr(state, 'fallback_round_count', 0) + 1
    phone = state.phone or ""
    license_plate = state.license_plate or ""
    problem_summary = state.problem_summary or ""
    entry_problem = state.entry_problem or ""
    conversation_history = state.conversation_history or []
    conversation_truncate_index = state.conversation_truncate_index or 0

    # 提取手机号
    phone_match = re.search(r'1[3-9]\d{9}', user_message)
    extracted_phone = phone_match.group(0) if phone_match else ""
    if extracted_phone:
        phone = extracted_phone

    # 提取车牌号
    msg_no_space = user_message.replace(" ", "")
    plate_pattern = r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{4,6}[A-Z0-9 挂学警港澳]?'
    plate_match = re.search(plate_pattern, msg_no_space)
    extracted_plate = plate_match.group(0) if plate_match else ""
    if extracted_plate:
        license_plate = extracted_plate

    # 第一次进入，记录问题
    if not entry_problem:
        problem_text = user_message
        if extracted_phone:
            problem_text = problem_text.replace(extracted_phone, "")
        if extracted_plate:
            problem_text = problem_text.replace(extracted_plate, "")
        problem_text = problem_text.strip()
        if problem_text:
            entry_problem = problem_text
            problem_summary = entry_problem.replace("用户", "您")

    # 检查确认词
    if _is_confirm(user_message):
        has_phone = bool(phone)
        has_license = bool(license_plate)
        has_problem = bool(problem_summary or entry_problem)

        if has_phone and has_license and has_problem:
            # 信息完整，创建工单
            reply_content = "✅ 收到您的问题，我们的工作人员将会尽快处理，并在 1-3 个工作日内联系您。"

            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase="done",
                fallback_round_count=fallback_round,
                phone=phone,
                license_plate=license_plate,
                problem_summary=problem_summary or entry_problem,
                user_supplement="",
                entry_problem=entry_problem,
                case_confirmed=True,
                conversation_truncate_index=conversation_truncate_index
            )
        else:
            # 信息不完整，让用户补充
            phase = "collect_info"

            info_parts = []
            if phone:
                info_parts.append(f"手机号：{phone}")
            if license_plate:
                info_parts.append(f"车牌号：{license_plate}")
            if problem_summary:
                info_parts.append(f"情况：{problem_summary}")

            missing = []
            if not phone:
                missing.append("手机号")
            if not license_plate:
                missing.append("车牌号")
            if not problem_summary and not entry_problem:
                missing.append("问题描述")

            if info_parts:
                reply_content = "好的，我先整理一下已有的信息：\n" + "\n".join(info_parts) + "\n麻烦再提供一下您的" + "和".join(missing) + "好吗？"
            else:
                reply_content = "麻烦您提供一下您的" + "和".join(missing) + "好吗？"

            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase=phase,
                fallback_round_count=fallback_round,
                phone=phone,
                license_plate=license_plate,
                problem_summary=problem_summary,
                user_supplement="",
                entry_problem=entry_problem,
                case_confirmed=False,
                conversation_truncate_index=conversation_truncate_index
            )

    # ============================================
    # 分阶段追问逻辑
    # ============================================

    if fallback_round <= 2:
        # 第 1-2 轮：追问详情，不要手机号车牌号
        reply_content = _generate_followup_question(fallback_round, entry_problem, user_message)
        return FallbackOutput(
            reply_content=reply_content,
            fallback_phase="asking_details",
            fallback_round_count=fallback_round,
            phone=phone,
            license_plate=license_plate,
            problem_summary=problem_summary or entry_problem,
            user_supplement="",
            entry_problem=entry_problem,
            case_confirmed=False,
            conversation_truncate_index=conversation_truncate_index
        )

    if fallback_round <= 4:
        # 第 3-4 轮：收集手机号和车牌号
        missing = []
        if not phone:
            missing.append("手机号")
        if not license_plate:
            missing.append("车牌号")

        if missing:
            reply_content = "好的，您的情况我了解了。为了帮您创建工单，麻烦提供一下您的" + "和".join(missing) + "好吗？"
        else:
            # 信息已完整，进入确认阶段
            reply_content = f"""好的，我总结一下您的问题：
手机号：{phone}
车牌号：{license_plate}
情况：{problem_summary or entry_problem}

以上信息准确吗？准确的话回复"确认"，有误的话请告诉我～"""

        return FallbackOutput(
            reply_content=reply_content,
            fallback_phase="collecting_contact",
            fallback_round_count=fallback_round,
            phone=phone,
            license_plate=license_plate,
            problem_summary=problem_summary or entry_problem,
            user_supplement="",
            entry_problem=entry_problem,
            case_confirmed=False,
            conversation_truncate_index=conversation_truncate_index
        )

    # 第 5 轮+：信息应该已经完整了，直接确认
    has_phone = bool(phone)
    has_license = bool(license_plate)
    has_problem = bool(problem_summary or entry_problem)

    if has_phone and has_license and has_problem:
        reply_content = f"""好的，我总结一下您的问题：
手机号：{phone}
车牌号：{license_plate}
情况：{problem_summary or entry_problem}

以上信息准确吗？准确的话回复"确认"，有误的话请告诉我～"""
    else:
        reply_content = "好的，您的情况我了解了。为了帮您创建工单，麻烦提供一下您的手机号和车牌号好吗？"

    return FallbackOutput(
        reply_content=reply_content,
        fallback_phase="confirm",
        fallback_round_count=fallback_round,
        phone=phone,
        license_plate=license_plate,
        problem_summary=problem_summary or entry_problem,
        user_supplement="",
        entry_problem=entry_problem,
        case_confirmed=False,
        conversation_truncate_index=conversation_truncate_index
    )


def _generate_followup_question(round_num: int, entry_problem: str, user_message: str) -> str:
    """生成追问问题"""

    if round_num == 1:
        # 第一轮：追问原因/详情
        return "好的，请问您具体遇到了什么情况？能详细说说吗？比如是在哪个平台充电的、什么时候、在哪里、遇到了什么问题？"

    if round_num == 2:
        # 第二轮：继续追问细节
        return "明白了。请问您是在哪个平台或小程序充电的呢？有订单号或者支付记录吗？大概是什么时间在哪里充的？"

    return "好的，您的情况我了解了。为了帮您创建工单，麻烦提供一下您的手机号和车牌号好吗？"
