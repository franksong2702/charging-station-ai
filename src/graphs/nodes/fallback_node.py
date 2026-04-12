"""
兜底流程节点 - 简化版 4 阶段流程

核心原则：
1. 好的，我会帮您记录并反馈给工作人员～
2. 收集信息：手机号、车牌号、时间、地点、问题详情
3. 生成问题总结
4. 用户确认后创建工单 + 发送邮件
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


def _is_cancel(user_message: str) -> bool:
    """判断用户是否在取消"""
    cancel_keywords = [
        "取消", "算了", "不用了", "不需要", "不弄了", "放弃", "停止", "结束",
        "没事了", "就这样吧", "别管了", "当我没说"
    ]
    msg = re.sub(r'[，。！？、\.\,\!\?\~\s]', '', user_message.lower())
    for keyword in cancel_keywords:
        if keyword in msg:
            return True
    return False


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


def _get_apology_message(user_message: str) -> str:
    """根据用户的愤怒程度，返回合适的安抚话术"""
    if _detect_anger(user_message):
        return "非常抱歉给您带来了不好的体验！"
    else:
        return "好的，我会帮您记录并反馈给工作人员～"


def _extract_info_by_simple_regex(user_message: str) -> dict:
    """
    简单的正则提取信息（不依赖 LLM）
    提取：手机号、车牌号、时间、地点、问题
    """
    result = {
        "phone": "",
        "license_plate": "",
        "time": "",
        "location": "",
        "problem": ""
    }
    
    # 提取手机号
    phone_match = re.search(r'1[3-9]\d{9}', user_message)
    if phone_match:
        result["phone"] = phone_match.group(0)
    
    # 提取车牌号
    plate_match = re.search(r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{4,5}[A-Z0-9挂学警港澳]?', user_message)
    if plate_match:
        result["license_plate"] = plate_match.group(0)
    
    # 提取时间
    time_keywords = ["今天", "昨天", "前天", "刚才", "刚刚", "早上", "上午", "中午", "下午", "晚上", "分钟", "小时", "点"]
    for keyword in time_keywords:
        if keyword in user_message:
            # 简单提取包含时间关键词的片段
            result["time"] = keyword
            break
    
    # 提取地点
    location_keywords = ["充电站", "充电桩", "站", "园", "广场", "商场", "路", "号"]
    for keyword in location_keywords:
        if keyword in user_message:
            # 简单提取包含地点关键词的片段
            result["location"] = keyword
            break
    
    # 如果没有提取到问题，就用整个用户消息
    if not result["problem"]:
        # 排除手机号和车牌号的部分，剩下的作为问题
        problem_text = user_message
        if result["phone"]:
            problem_text = problem_text.replace(result["phone"], "")
        if result["license_plate"]:
            problem_text = problem_text.replace(result["license_plate"], "")
        problem_text = problem_text.strip()
        if problem_text:
            result["problem"] = problem_text
    
    return result


def fallback_node(state: FallbackInput, config: RunnableConfig, runtime: Runtime[Context]) -> FallbackOutput:
    """
    title: 兜底流程处理 - 简化版
    desc: 4 阶段流程：记录反馈 → 收集信息 → 总结确认 → 创建工单
    """
    ctx = runtime.context
    
    # 从状态中获取当前信息
    user_message = state.user_message
    phase = state.fallback_phase or ""
    phone = state.phone or ""
    license_plate = state.license_plate or ""
    problem_summary = state.problem_summary or ""
    entry_problem = state.entry_problem or ""
    conversation_history = state.conversation_history or []
    conversation_truncate_index = state.conversation_truncate_index or 0
    
    # 默认回复
    reply_content = "好的，我会帮您记录并反馈给工作人员～"
    
    # 记录截断索引
    if conversation_truncate_index == 0:
        conversation_truncate_index = len(conversation_history)
    
    logger.info(f"兜底流程 - 当前阶段: {phase}, 手机号: {phone}, 车牌号: {license_plate}")
    
    # ==================== 1. 先检查全局确认词 ====================
    if _is_confirm(user_message):
        logger.info(f"兜底流程 - 全局确认词识别")
        
        # 检查信息是否完整
        has_phone = bool(phone)
        has_license = bool(license_plate)
        has_problem = bool(problem_summary or entry_problem)
        
        if has_phone and has_license and has_problem:
            # 信息完整，直接创建工单
            reply_content = "✅ 收到您的问题，我们的工作人员将会尽快处理，并在1-3个工作日内联系您。"
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
            # 信息不完整，先整理信息让用户补充
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
    
    # ==================== 2. 检查取消 ====================
    if _is_cancel(user_message):
        logger.info("兜底流程 - 用户取消")
        return FallbackOutput(
            reply_content="好的，理解！如有需要随时联系我们。祝您生活愉快～",
            fallback_phase="",
            phone="",
            license_plate="",
            problem_summary="",
            user_supplement="",
            entry_problem="",
            case_confirmed=False,
            conversation_truncate_index=0
        )
    
    # ==================== 3. 提取用户提供的信息（简单正则，不依赖 LLM） ====================
    extracted = _extract_info_by_simple_regex(user_message)
    extracted_phone = extracted.get("phone", "")
    extracted_plate = extracted.get("license_plate", "")
    extracted_time = extracted.get("time", "")
    extracted_location = extracted.get("location", "")
    extracted_problem = extracted.get("problem", "")
    
    # 更新信息
    if extracted_phone:
        phone = extracted_phone
    if extracted_plate:
        license_plate = extracted_plate
    
    # 更新问题描述
    if not entry_problem:
        # 第一次进入，记录 entry_problem
        entry_problem = extracted_problem or user_message
        problem_summary = entry_problem.replace("用户", "您")
    elif extracted_problem and extracted_problem != entry_problem:
        # 补充新信息
        new_details = []
        if extracted_time:
            new_details.append(f"时间：{extracted_time}")
        if extracted_location:
            new_details.append(f"地点：{extracted_location}")
        if new_details:
            problem_summary = f"{problem_summary}，{'，'.join(new_details)}"
    
    # ==================== 4. 判断当前阶段，执行对应逻辑 ====================
    
    # 阶段 1：刚开始（ask_problem 或 空）
    if phase == "" or phase == "ask_problem":
        phase = "collect_info"
        apology_msg = _get_apology_message(user_message)
        reply_content = f"""{apology_msg}
方便提供一下您的手机号和车牌号吗？"""
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
    
    # 阶段 2：收集信息（collect_info）
    if phase == "collect_info":
        # 检查是否信息完整
        has_phone = bool(phone)
        has_license = bool(license_plate)
        has_problem = bool(problem_summary)
        
        if has_phone and has_license and has_problem:
            # 信息完整，进入确认阶段
            phase = "confirm"
            reply_content = f"""好的，我整理一下您的问题：
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
    
    # 阶段 3：确认阶段（confirm）
    if phase == "confirm":
        # 用户确认后应该已经在前面的全局确认词检查中处理了
        # 如果到了这里，说明用户在纠正信息
        # 继续收集信息
        phase = "collect_info"
        reply_content = f"""好的，我会帮您记录并反馈给工作人员～
麻烦提供一下您的信息好吗？"""
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
