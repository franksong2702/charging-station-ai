"""
兜底流程节点 - 生产版本

修复方案：
1. 简化信息提取逻辑 - 确保车牌号被正确识别
2. 超简单直接的逻辑，避免复杂状态管理
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
    title: 兜底流程处理 - 生产版本
    desc: 超简单直接的 4 阶段流程
    """
    ctx = runtime.context

    # 从状态中获取当前信息
    user_message = state.user_message.strip()
    phase = state.fallback_phase or ""
    phone = state.phone or ""
    license_plate = state.license_plate or ""
    problem_summary = state.problem_summary or ""
    entry_problem = state.entry_problem or ""
    conversation_history = state.conversation_history or []
    conversation_truncate_index = state.conversation_truncate_index or 0

    # ==================== 1. 超简单直接的信息提取 ====================

    # 提取手机号 - 超简单
    phone_match = re.search(r'1[3-9]\d{9}', user_message)
    extracted_phone = phone_match.group(0) if phone_match else ""

    # 提取车牌号 - 超简单，支持中间有空格
    # 先去掉所有空格，再匹配
    msg_no_space = user_message.replace(" ", "")
    plate_pattern = r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{4,6}[A-Z0-9 挂学警港澳]?'
    plate_match = re.search(plate_pattern, msg_no_space)
    extracted_plate = plate_match.group(0) if plate_match else ""

    # 更新信息
    if extracted_phone:
        phone = extracted_phone
    if extracted_plate:
        license_plate = extracted_plate

    # 更新问题描述
    if not entry_problem:
        # 第一次进入，记录问题
        problem_text = user_message
        if extracted_phone:
            problem_text = problem_text.replace(extracted_phone, "")
        if extracted_plate:
            problem_text = problem_text.replace(extracted_plate, "")
        problem_text = problem_text.strip()
        if problem_text:
            entry_problem = problem_text
            problem_summary = entry_problem.replace("用户", "您")

    # ==================== 2. 检查全局确认词 ====================

    if _is_confirm(user_message):
        # 检查信息是否完整
        has_phone = bool(phone)
        has_license = bool(license_plate)
        has_problem = bool(problem_summary or entry_problem)

        if has_phone and has_license and has_problem:
            # 信息完整，创建工单
            reply_content = "✅ 收到您的问题，我们的工作人员将会尽快处理，并在 1-3 个工作日内联系您。"

            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase="done",
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
                phone=phone,
                license_plate=license_plate,
                problem_summary=problem_summary,
                user_supplement="",
                entry_problem=entry_problem,
                case_confirmed=False,
                conversation_truncate_index=conversation_truncate_index
            )

    # ==================== 3. 判断当前阶段 ====================

    # 阶段 1：刚开始
    if phase == "":
        phase = "collect_info"
        reply_content = "好的，我会帮您记录并反馈给工作人员～\n方便提供一下您的手机号和车牌号吗？"

        return FallbackOutput(
            reply_content=reply_content,
            fallback_phase=phase,
            phone=phone,
            license_plate=license_plate,
            problem_summary=problem_summary,
            user_supplement="",
            entry_problem=entry_problem,
            case_confirmed=False,
            conversation_truncate_index=conversation_truncate_index
        )

    # 阶段 2：收集信息
    if phase == "collect_info":
        # 检查是否信息完整
        has_phone = bool(phone)
        has_license = bool(license_plate)
        has_problem = bool(problem_summary)

        if has_phone and has_license and has_problem:
            # 信息完整，进入确认阶段
            phase = "confirm"
            reply_content = f"""好的，我总结一下您的问题：
手机号：{phone}
车牌号：{license_plate}
情况：{problem_summary}

以上信息准确吗？准确的话回复"确认"，有误的话请告诉我～"""

            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase=phase,
                phone=phone,
                license_plate=license_plate,
                problem_summary=problem_summary,
                user_supplement="",
                entry_problem=entry_problem,
                case_confirmed=False,
                conversation_truncate_index=conversation_truncate_index
            )
        else:
            # 信息不完整，继续收集
            missing = []
            if not phone:
                missing.append("手机号")
            if not license_plate:
                missing.append("车牌号")
            if not problem_summary:
                missing.append("问题描述")

            reply_content = f"""好的，我会帮您记录并反馈给工作人员～
麻烦提供一下您的{"和".join(missing)}好吗？"""

            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase=phase,
                phone=phone,
                license_plate=license_plate,
                problem_summary=problem_summary,
                user_supplement="",
                entry_problem=entry_problem,
                case_confirmed=False,
                conversation_truncate_index=conversation_truncate_index
            )

    # 阶段 3：确认阶段
    if phase == "confirm":
        # 回到收集阶段
        phase = "collect_info"
        reply_content = "好的，我会帮您记录并反馈给工作人员～\n麻烦提供一下您的信息好吗？"

        return FallbackOutput(
            reply_content=reply_content,
            fallback_phase=phase,
            phone=phone,
            license_plate=license_plate,
            problem_summary=problem_summary,
            user_supplement="",
            entry_problem=entry_problem,
            case_confirmed=False,
            conversation_truncate_index=conversation_truncate_index
        )

    # 默认：继续收集信息
    phase = "collect_info"
    reply_content = "好的，我会帮您记录并反馈给工作人员～\n麻烦提供一下您的信息好吗？"

    return FallbackOutput(
        reply_content=reply_content,
        fallback_phase=phase,
        phone=phone,
        license_plate=license_plate,
        problem_summary=problem_summary,
        user_supplement="",
        entry_problem=entry_problem,
        case_confirmed=False,
        conversation_truncate_index=conversation_truncate_index
    )
