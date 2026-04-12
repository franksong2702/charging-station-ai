"""
兜底流程节点 - 修复版 4 阶段流程

修复的问题：
1. 车牌号正则不匹配 - 支持新能源车牌，支持中间有空格
2. 确认词识别后没有生成总结 - 正确处理确认流程
3. 信息提取出现乱码 - 修复正则提取逻辑
4. 确认后没有创建工单和发送邮件 - 确保流程正确
"""
import os
import json
import logging
import re
import sys

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import FallbackInput, FallbackOutput

# 配置日志
logger = logging.getLogger(__name__)


def _is_confirm(user_message: str) -> bool:
    """判断用户是否在确认"""
    print(f"DEBUG: _is_confirm 输入={user_message}")
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
                print(f"DEBUG: _is_confirm 排除否定词，返回 False")
                return False
    
    for keyword in confirm_keywords:
        if keyword in msg:
            print(f"DEBUG: _is_confirm 匹配关键词 '{keyword}'，返回 True")
            return True
    print(f"DEBUG: _is_confirm 未匹配，返回 False")
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


def _extract_info(user_message: str) -> dict:
    """
    提取用户消息中的信息
    提取：手机号、车牌号、时间、地点、问题
    """
    print(f"===== _extract_info 开始 =====")
    print(f"DEBUG: 用户输入={user_message}")
    
    result = {
        "phone": "",
        "license_plate": "",
        "time": "",
        "location": "",
        "problem": ""
    }
    
    # 1. 提取手机号 - 简单直接
    phone_match = re.search(r'1[3-9]\d{9}', user_message)
    print(f"DEBUG: 手机号匹配={phone_match}")
    if phone_match:
        result["phone"] = phone_match.group(0)
        logger.info(f"提取手机号成功: {result['phone']}")
        print(f"DEBUG: 提取手机号成功: {result['phone']}")
    
    # 2. 提取车牌号 - 支持新能源车牌，支持中间有空格
    # 格式：京 A12345, 京 AD12345, 沪 A12345D, 京AD12345
    # 支持中间有空格的情况
    plate_pattern = r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领].{0,3}[A-Z0-9]{5,7}[A-Z0-9挂学警港澳]?'
    plate_match = re.search(plate_pattern, user_message)
    print(f"DEBUG: 车牌号匹配={plate_match}")
    if plate_match:
        # 去除中间的空格和非字母数字字符
        plate = re.sub(r'[^京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领A-Z0-9挂学警港澳]', '', plate_match.group(0))
        result["license_plate"] = plate
        logger.info(f"提取车牌号成功: {result['license_plate']}")
        print(f"DEBUG: 提取车牌号成功: {result['license_plate']}")
    
    # 3. 提取时间 - 简单关键词匹配
    time_keywords = ["今天", "昨天", "前天", "刚才", "刚刚", "早上", "上午", "中午", "下午", "晚上"]
    for keyword in time_keywords:
        if keyword in user_message:
            result["time"] = keyword
            logger.info(f"提取时间成功: {result['time']}")
            print(f"DEBUG: 提取时间成功: {result['time']}")
            break
    print(f"DEBUG: 时间匹配={result['time']}")
    
    # 4. 提取地点 - 简单关键词匹配
    if "充电站" in user_message:
        # 提取"充电站"前面的部分
        station_idx = user_message.find("充电站")
        if station_idx > 0:
            # 从前面找最近的标点或空格
            start_idx = max(
                user_message.rfind("，", 0, station_idx),
                user_message.rfind("。", 0, station_idx),
                user_message.rfind("！", 0, station_idx),
                user_message.rfind("？", 0, station_idx),
                user_message.rfind(" ", 0, station_idx)
            )
            if start_idx == -1:
                start_idx = 0
            else:
                start_idx += 1
            location_part = user_message[start_idx:station_idx+3].strip()
            if location_part:
                result["location"] = location_part
                logger.info(f"提取地点成功: {result['location']}")
                print(f"DEBUG: 提取地点成功: {result['location']}")
    print(f"DEBUG: 地点匹配={result['location']}")
    
    # 5. 提取问题 - 排除手机号和车牌号的部分
    problem_text = user_message
    if result["phone"]:
        problem_text = problem_text.replace(result["phone"], "")
    if result["license_plate"]:
        problem_text = problem_text.replace(result["license_plate"], "")
    problem_text = problem_text.strip()
    if problem_text and len(problem_text) > 2:
        result["problem"] = problem_text
        logger.info(f"提取问题成功: {result['problem']}")
        print(f"DEBUG: 提取问题成功: {result['problem']}")
    
    print(f"DEBUG: 最终提取结果={result}")
    print(f"===== _extract_info 结束 =====")
    return result


def fallback_node(state: FallbackInput, config: RunnableConfig, runtime: Runtime[Context]) -> FallbackOutput:
    """
    title: 兜底流程处理 - 修复版
    desc: 4 阶段流程：记录反馈 → 收集信息 → 总结确认 → 创建工单
    """
    print(f"===== fallback_node 开始 =====")
    
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
    
    print(f"DEBUG: 从状态读取的信息:")
    print(f"DEBUG:   user_message='{user_message}'")
    print(f"DEBUG:   phase='{phase}'")
    print(f"DEBUG:   phone='{phone}'")
    print(f"DEBUG:   license_plate='{license_plate}'")
    print(f"DEBUG:   problem_summary='{problem_summary}'")
    
    # 默认回复
    reply_content = "好的，我会帮您记录并反馈给工作人员～"
    
    # 记录截断索引
    if conversation_truncate_index == 0:
        conversation_truncate_index = len(conversation_history)
    
    logger.info(f"===== 兜底流程开始 =====")
    logger.info(f"用户消息: '{user_message}'")
    logger.info(f"当前阶段: {phase}")
    logger.info(f"已有信息 - 手机: '{phone}', 车牌: '{license_plate}', 问题: '{problem_summary}'")
    
    # ==================== 1. 先检查全局确认词（优先级最高） ====================
    print(f"DEBUG: 步骤 1: 检查全局确认词")
    if _is_confirm(user_message):
        logger.info("✓ 全局确认词识别")
        print(f"DEBUG: ✓ 全局确认词识别")
        
        # 检查信息是否完整
        has_phone = bool(phone)
        has_license = bool(license_plate)
        has_problem = bool(problem_summary or entry_problem)
        
        print(f"DEBUG: 信息完整性检查:")
        print(f"DEBUG:   has_phone={has_phone}")
        print(f"DEBUG:   has_license={has_license}")
        print(f"DEBUG:   has_problem={has_problem}")
        
        logger.info(f"信息完整性检查 - 手机: {has_phone}, 车牌: {has_license}, 问题: {has_problem}")
        
        if has_phone and has_license and has_problem:
            # ✓ 信息完整，直接创建工单
            logger.info("✓ 信息完整，创建工单")
            print(f"DEBUG: ✓ 信息完整，创建工单")
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
            # ✗ 信息不完整，先整理信息让用户补充
            logger.info("✗ 信息不完整，让用户补充")
            print(f"DEBUG: ✗ 信息不完整，让用户补充")
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
            
            print(f"DEBUG: 已收集信息={info_parts}")
            print(f"DEBUG: 缺失信息={missing}")
            
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
    print(f"DEBUG: 步骤 2: 检查取消")
    if _is_cancel(user_message):
        logger.info("用户取消")
        print(f"DEBUG: 用户取消")
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
    
    # ==================== 3. 提取用户提供的信息 ====================
    print(f"DEBUG: 步骤 3: 提取用户提供的信息")
    extracted = _extract_info(user_message)
    extracted_phone = extracted.get("phone", "")
    extracted_plate = extracted.get("license_plate", "")
    extracted_time = extracted.get("time", "")
    extracted_location = extracted.get("location", "")
    extracted_problem = extracted.get("problem", "")
    
    print(f"DEBUG: 提取结果:")
    print(f"DEBUG:   extracted_phone='{extracted_phone}'")
    print(f"DEBUG:   extracted_plate='{extracted_plate}'")
    print(f"DEBUG:   extracted_time='{extracted_time}'")
    print(f"DEBUG:   extracted_location='{extracted_location}'")
    print(f"DEBUG:   extracted_problem='{extracted_problem}'")
    
    # 更新信息
    if extracted_phone:
        phone = extracted_phone
        logger.info(f"更新手机号: {phone}")
        print(f"DEBUG: 更新手机号: {phone}")
    if extracted_plate:
        license_plate = extracted_plate
        logger.info(f"更新车牌号: {license_plate}")
        print(f"DEBUG: 更新车牌号: {license_plate}")
    
    # 更新问题描述
    if not entry_problem:
        # 第一次进入，记录 entry_problem
        entry_problem = extracted_problem or user_message
        problem_summary = entry_problem.replace("用户", "您")
        logger.info(f"第一次进入，记录问题: {problem_summary}")
        print(f"DEBUG: 第一次进入，记录问题: {problem_summary}")
    elif extracted_problem and extracted_problem != entry_problem:
        # 补充新信息
        new_details = []
        if extracted_time:
            new_details.append(f"时间：{extracted_time}")
        if extracted_location:
            new_details.append(f"地点：{extracted_location}")
        
        if new_details:
            problem_summary = f"{problem_summary}，{'，'.join(new_details)}"
            logger.info(f"补充问题细节: {problem_summary}")
            print(f"DEBUG: 补充问题细节: {problem_summary}")
    
    print(f"DEBUG: 更新后的状态:")
    print(f"DEBUG:   phone='{phone}'")
    print(f"DEBUG:   license_plate='{license_plate}'")
    print(f"DEBUG:   problem_summary='{problem_summary}'")
    
    # ==================== 4. 判断当前阶段，执行对应逻辑 ====================
    print(f"DEBUG: 步骤 4: 判断当前阶段")
    
    # 阶段 1：刚开始（空）
    if phase == "":
        phase = "collect_info"
        apology_msg = _get_apology_message(user_message)
        reply_content = f"""{apology_msg}
方便提供一下您的手机号和车牌号吗？"""
        logger.info(f"阶段 1: 刚开始，回复: {reply_content}")
        print(f"DEBUG: 阶段 1: 刚开始，回复: {reply_content}")
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
        logger.info(f"阶段 2: 收集信息")
        print(f"DEBUG: 阶段 2: 收集信息")
        
        # 检查是否信息完整
        has_phone = bool(phone)
        has_license = bool(license_plate)
        has_problem = bool(problem_summary)
        
        logger.info(f"信息完整性 - 手机: {has_phone}, 车牌: {has_license}, 问题: {has_problem}")
        print(f"DEBUG: 信息完整性 - 手机: {has_phone}, 车牌: {has_license}, 问题: {has_problem}")
        
        if has_phone and has_license and has_problem:
            # ✓ 信息完整，进入确认阶段
            phase = "confirm"
            
            # 构建问题总结
            summary_parts = [problem_summary]
            if extracted_time:
                summary_parts.append(f"时间：{extracted_time}")
            if extracted_location:
                summary_parts.append(f"地点：{extracted_location}")
            
            final_summary = "，".join(summary_parts)
            
            reply_content = f"""好的，我总结一下您的问题：
手机号：{phone}
车牌号：{license_plate}
情况：{final_summary}

以上信息准确吗？准确的话回复"确认"，有误的话请告诉我～"""
            
            logger.info(f"信息完整，进入确认阶段，回复: {reply_content}")
            print(f"DEBUG: 信息完整，进入确认阶段，回复: {reply_content}")
            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase=phase,
                phone=phone,
                license_plate=license_plate,
                problem_summary=final_summary,
                user_supplement="",
                entry_problem=entry_problem,
                case_confirmed=False,
                conversation_truncate_index=conversation_truncate_index
            )
        else:
            # ✗ 信息不完整，继续收集
            missing = []
            if not phone:
                missing.append("手机号")
            if not license_plate:
                missing.append("车牌号")
            if not problem_summary:
                missing.append("问题描述")
            
            print(f"DEBUG: 信息不完整，缺失: {missing}")
            
            reply_content = f"""好的，我会帮您记录并反馈给工作人员～
麻烦提供一下您的{"和".join(missing)}好吗？"""
            
            logger.info(f"信息不完整，继续收集，回复: {reply_content}")
            print(f"DEBUG: 信息不完整，继续收集，回复: {reply_content}")
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
        logger.info(f"阶段 3: 确认阶段")
        print(f"DEBUG: 阶段 3: 确认阶段")
        # 用户确认后应该已经在前面的全局确认词检查中处理了
        # 如果到了这里，说明用户在纠正信息，回到收集阶段
        phase = "collect_info"
        
        # 再次提取用户可能提供的新信息
        extracted_new = _extract_info(user_message)
        if extracted_new.get("phone"):
            phone = extracted_new["phone"]
        if extracted_new.get("license_plate"):
            license_plate = extracted_new["license_plate"]
        
        reply_content = f"""好的，我会帮您记录并反馈给工作人员～
麻烦提供一下您的信息好吗？"""
        
        logger.info(f"回到收集阶段，回复: {reply_content}")
        print(f"DEBUG: 回到收集阶段，回复: {reply_content}")
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
    logger.info(f"默认：继续收集信息")
    print(f"DEBUG: 默认：继续收集信息")
    phase = "collect_info"
    
    print(f"===== fallback_node 结束 =====")
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
