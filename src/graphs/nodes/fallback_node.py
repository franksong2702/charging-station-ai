"""
兜底流程节点 - 处理需要人工介入的场景

核心原则：
1. 态度与澄清原则：先安抚，问清楚问题，尽量挡投诉
2. 总结与确认原则：进入兜底后先总结问题，再收集手机号和车牌号

优化点：
1. 新增"共情追问"阶段（ask_problem）：先问清楚问题，安抚情绪
2. 新增"澄清安抚"阶段（clarify）：收集详情（地点、时间等）
3. 新增"总结与收集"阶段（summary_collect）：再收集手机号和车牌号
4. 用户说什么就记什么，要改什么就改什么，最后确认
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

from graphs.state import FallbackInput, FallbackOutput, SummaryInput
from graphs.nodes.summary_agent_node import summary_agent_node

# 配置日志
logger = logging.getLogger(__name__)


def _is_confirm(user_message: str) -> bool:
    """判断用户是否在确认"""
    # 确认关键词（去掉标点后匹配）- 包含用户要求的所有同义词
    confirm_keywords = [
        "确认", "确认无误", "没问题", "是的", "对", "对的", "好的", "行", "可以", "可以的",
        "准确", "没错", "对了", "正确", "就是这样", "同意", "好", "嗯", "嗯嗯",
        "要得", "ok", "okay", "OK", "收到"
    ]
    # 先去掉标点符号
    msg = re.sub(r'[，。！？、\.\,\!\?\~\s]', '', user_message.lower())
    
    # 特殊处理：排除否定词
    # 如果消息以"不"开头且后面跟着确认词，排除（如"不对"、"不行"）
    if msg.startswith("不") and len(msg) > 1:
        # 检查"不"后面的部分是否是确认词
        rest = msg[1:]
        for keyword in confirm_keywords:
            if keyword in rest:
                return False
    
    # 正常匹配
    for keyword in confirm_keywords:
        if keyword in msg:
            return True
    return False


def _is_cancel(user_message: str) -> bool:
    """判断用户是否在取消"""
    # 取消关键词（去掉标点后匹配）
    cancel_keywords = [
        "取消", "算了", "不用了", "不需要", "不弄了", "放弃", "停止", "结束",
        "没事了", "就这样吧", "别管了", "当我没说"
    ]
    # 先去掉标点符号
    msg = re.sub(r'[，。！？、\.\,\!\?\~\s]', '', user_message.lower())
    for keyword in cancel_keywords:
        if keyword in msg:
            return True
    return False


def _detect_anger(user_message: str) -> bool:
    """
    判断用户是否表达了愤怒或强烈不满
    :param user_message: 用户消息
    :return: 是否愤怒
    """
    # 愤怒/强烈不满关键词
    anger_keywords = [
        "什么破系统", "垃圾系统", "气死我了", "太差了", "什么垃圾", "破系统", 
        "烂系统", "什么东西", "太差劲", "太烂", "什么玩意儿", "破玩意儿",
        "垃圾", "太差", "气死", "太气人"
    ]
    # 先去掉标点符号
    msg = re.sub(r'[，。！？、\.\,\!\?\~\s]', '', user_message.lower())
    for keyword in anger_keywords:
        if keyword in msg:
            return True
    return False


def _get_apology_message(user_message: str) -> str:
    """
    根据用户的愤怒程度，返回合适的安抚话术
    :param user_message: 用户消息
    :return: 安抚话术
    """
    if _detect_anger(user_message):
        # 强烈愤怒，使用更强的安抚
        apology_options = [
            "非常抱歉给您带来了不好的体验！我理解您现在很生气，我先帮您看看问题。",
            "真的非常抱歉让您遇到这样的问题！我能理解您的心情，我先帮您处理。",
            "很抱歉让您有不愉快的体验！请您消消气，我来帮您看看怎么解决。"
        ]
        import random
        return random.choice(apology_options)
    else:
        # 一般情况，正常安抚
        return "非常抱歉给您带来了不好的体验！"


def _extract_info_by_regex(user_message: str) -> dict:
    """
    使用正则表达式提取手机号和车牌号（作为 LLM 的兜底机制）
    :param user_message: 用户消息
    :return: 包含 phone, license_plate 的字典
    """
    import re
    
    result = {
        "phone": "",
        "license_plate": ""
    }
    
    # 【预处理】去除用户消息中的所有空格，便于匹配
    cleaned_message = re.sub(r'\s+', '', user_message)
    
    # 1. 提取手机号：11位数字，以1开头
    phone_pattern = r'1\d{10}'
    phone_matches = re.findall(phone_pattern, cleaned_message)
    if phone_matches:
        result["phone"] = phone_matches[0]
    
    # 2. 提取车牌号：中文省份简称 + 字母 + 数字/字母（普通蓝牌、绿牌等）
    # 匹配规则：
    # - 省份简称（京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼）
    # - 1个字母
    # - 5-6位数字/字母（支持绿牌的6位）
    # 【优化】先在原始消息中匹配（允许空格），如果没匹配到再在清理后的消息中匹配
    plate_pattern_with_space = r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]\s*[A-Z]\s*[A-Z0-9]{5,6}'
    plate_matches = re.findall(plate_pattern_with_space, user_message.upper())
    
    if plate_matches:
        # 匹配到了，去除结果中的空格
        result["license_plate"] = re.sub(r'\s+', '', plate_matches[0])
    else:
        # 在原始消息中没匹配到，试试清理后的消息
        plate_pattern_no_space = r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{5,6}'
        plate_matches_clean = re.findall(plate_pattern_no_space, cleaned_message.upper())
        if plate_matches_clean:
            result["license_plate"] = plate_matches_clean[0]
    
    return result


def _extract_info_by_llm(ctx: Context, user_message: str, check_complaint: bool = False) -> dict:
    """
    使用 LLM 从用户消息中提取手机号、车牌号、问题描述、时间、地点
    :param ctx: 运行上下文
    :param user_message: 用户消息
    :param check_complaint: 是否检测抱怨，如果是则自动生成道歉话术
    :return: 包含 phone, license_plate, problem, time, location, extra_apology 的字典
    """
    # 【新增】先用正则表达式提取（兜底机制）
    regex_result = _extract_info_by_regex(user_message)
    regex_phone = regex_result.get("phone", "")
    regex_plate = regex_result.get("license_plate", "")
    
    # 如果正则已经提取到了，直接返回（避免 LLM 犯错）
    if regex_phone or regex_plate:
        logger.info(f"兜底流程 - 正则提取成功: phone='{regex_phone}', plate='{regex_plate}'")
        return {
            "phone": regex_phone,
            "license_plate": regex_plate,
            "problem": "",
            "time": "",
            "location": "",
            "extra_apology": ""
        }
    
    # 创建 LLM 客户端
    llm_client = create_llm_client(ctx)
    
    # 提示词
    prompt = f"""请从用户消息中提取以下信息，并以JSON格式返回：

1. phone: 用户提供的手机号（如果有）
2. license_plate: 用户提供的车牌号（如果有）
3. problem: 用户描述的问题（如果有）
4. time: 用户提到的时间（如果有，例如"今天早上"、"3点"等）
5. location: 用户提到的地点（如果有，例如"XX充电站"、"家附近"等）

用户消息："{user_message}"

示例输出1（有手机号、车牌号、问题）：
{{
    "phone": "13812345678",
    "license_plate": "沪A12345",
    "problem": "充电桩充不上电",
    "time": "",
    "location": ""
}}

示例输出2（只有问题）：
{{
    "phone": "",
    "license_plate": "",
    "problem": "充电桩坏了",
    "time": "今天下午",
    "location": "万达充电站"
}}

示例输出3（语音输入分段）：
用户说"手机号139。16425678。车牌号。沪a Dr 3509。"
{{
    "phone": "13916425678",
    "license_plate": "沪ADR3509",
    "problem": "",
    "time": "",
    "location": ""
}}

注意事项：
1. 手机号提取：只提取数字，忽略空格和标点
2. 车牌号提取：去除空格，字母统一大写
3. 问题提取：完整保留用户问题描述
4. 如果没有某项信息，返回空字符串""
5. 只返回JSON，不要有其他文字
"""
    
    # 调用 LLM
    try:
        response = llm_client.invoke([HumanMessage(content=prompt)])
        response_text = response.content.strip()
        
        # 解析 JSON
        # 有时候 LLM 会返回 markdown 格式的代码块，需要先提取
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        # 容错处理：如果 JSON 解析失败，返回默认值
        try:
            result = json.loads(response_text.strip())
            # 确保返回的字段存在
            return {
                "phone": result.get("phone", ""),
                "license_plate": result.get("license_plate", ""),
                "problem": result.get("problem", ""),
                "time": result.get("time", ""),
                "location": result.get("location", ""),
                "extra_apology": ""
            }
        except json.JSONDecodeError:
            logger.warning(f"LLM 返回的 JSON 解析失败: {response_text}")
            return {
                "phone": "",
                "license_plate": "",
                "problem": "",
                "time": "",
                "location": "",
                "extra_apology": ""
            }
    
    except Exception as e:
        logger.error(f"调用 LLM 提取信息失败: {e}")
        return {
            "phone": "",
            "license_plate": "",
            "problem": "",
            "time": "",
            "location": "",
            "extra_apology": ""
        }


def fallback_node(state: FallbackInput, config: RunnableConfig, runtime: Runtime[Context]) -> FallbackOutput:
    """
    title: 兜底流程处理
    desc: 处理投诉和兜底场景，收集信息、安抚用户、创建工单
    """
    ctx = runtime.context
    
    # 从状态中获取当前信息
    user_message = state.user_message
    phase = state.fallback_phase or ""
    phone = state.phone or ""
    license_plate = state.license_plate or ""
    problem_summary = state.problem_summary or ""
    user_supplement = state.user_supplement or ""
    entry_problem = state.entry_problem or ""
    conversation_history = state.conversation_history or []
    conversation_truncate_index = state.conversation_truncate_index or 0
    
    # 【修复】给 reply_content 一个默认值，确保在所有情况下都被赋值
    reply_content = "非常抱歉，让我帮您处理这个问题。"
    
    # 记录截断索引（如果还没有记录）
    if conversation_truncate_index == 0:
        conversation_truncate_index = len(conversation_history)
        logger.info(f"兜底流程 - 记录对话截断索引: {conversation_truncate_index}")
    
    logger.info(f"兜底流程 - 当前阶段: {phase}, 手机号: {phone}, 车牌号: {license_plate}")
    
    # ==================== 【新增】全局确认词检查（任何阶段都能识别） ====================
    # 先检查用户是否在确认（不管在什么阶段）
    if _is_confirm(user_message):
        logger.info(f"兜底流程 - 全局确认词识别，当前阶段: {phase}")
        
        # 检查信息是否完整
        has_phone = bool(phone)
        has_license = bool(license_plate)
        has_problem = bool(problem_summary)
        
        # 如果信息完整，直接创建工单
        if has_phone and has_license and has_problem:
            logger.info(f"兜底流程 - 信息完整，直接创建工单")
            reply_content = "✅ 收到您的问题，我们的工作人员将会尽快处理，并在1-3个工作日内联系您。\n手机号：" + phone + "\n车牌号：" + license_plate + "\n情况：" + problem_summary
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
        
        # 如果信息不完整，先整理信息让用户确认
        logger.info(f"兜底流程 - 信息不完整，整理信息让用户确认")
        phase = "confirm"
        
        # 构建信息展示
        info_parts = []
        if phone:
            info_parts.append("手机号：" + phone)
        if license_plate:
            info_parts.append("车牌号：" + license_plate)
        if problem_summary:
            info_parts.append("情况：" + problem_summary)
        
        # 询问缺失信息
        missing = []
        if not phone:
            missing.append("手机号")
        if not license_plate:
            missing.append("车牌号")
        if not problem_summary:
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
    
    # ==================== 取消/退出兜底流程 ====================
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
    
    # ==================== 【新增】共情追问阶段 ====================
    if phase == "ask_problem" or (phase == "" and not entry_problem):
        # 【修复 FALL-002/COMP-003】先共情追问，再收集信息
        # 1. 先安抚情绪
        apology_msg = _get_apology_message(user_message)
        
        # 2. 判断用户是否已提供问题描述
        has_problem = len(user_message) >= 2 and "手机" not in user_message and "车牌" not in user_message
        
        if has_problem:
            # 用户已提供问题，进入 clarify 阶段收集详情（地点、时间等）
            entry_problem = user_message
            phase = "clarify"
            # 简单设置 problem_summary
            problem_summary = entry_problem.replace("用户", "您")
            # 回复用户
            reply_content = f"""{apology_msg}
我已经记录了您的问题：
{problem_summary}
请问还能告诉我更多细节吗？比如具体发生在什么时间、什么地点？"""
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
            # 用户还没提供问题，继续追问
            phase = "ask_problem"
            if "退款" in user_message or "退钱" in user_message:
                reply_content = f"""{apology_msg}
请问您是想了解退款规则，还是有具体的订单需要退款呢？

如果是想了解规则，我可以直接告诉您；如果是有具体订单需要处理，我来帮您登记反馈～"""
            else:
                reply_content = f"""{apology_msg}
请问您遇到了什么问题？我先帮您看看～"""
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
    
    # ==================== 澄清安抚阶段（收集详情：地点、时间等） ====================
    if phase == "clarify":
        # 1. 先提取用户可能提供的手机号、车牌号、问题信息、时间、地点
        extracted = _extract_info_by_llm(ctx, user_message, check_complaint=False)
        extracted_phone = extracted.get("phone", "")
        extracted_plate = extracted.get("license_plate", "")
        extracted_problem = extracted.get("problem", "")
        extracted_time = extracted.get("time", "")
        extracted_location = extracted.get("location", "")
        
        # 2. 更新手机号和车牌号
        if extracted_phone:
            phone = extracted_phone
        if extracted_plate:
            license_plate = extracted_plate
        
        # 3. 更新问题描述（如果用户提供了新的问题或详情）
        updated = []
        if extracted_problem and not problem_summary:
            # 没有旧的问题总结，用新提取的
            entry_problem = extracted_problem
            problem_summary = entry_problem.replace("用户", "您")
            updated.append(f"情况 {problem_summary}")
        elif extracted_problem and problem_summary:
            # 有旧的问题总结，补充新的信息
            if extracted_time or extracted_location:
                new_details = []
                if extracted_time:
                    new_details.append(f"时间：{extracted_time}")
                if extracted_location:
                    new_details.append(f"地点：{extracted_location}")
                if new_details:
                    problem_summary = f"{problem_summary}，{'，'.join(new_details)}"
                    updated.append(f"情况 {problem_summary}")
        
        # 4. 判断是否应该进入 summary_collect 阶段
        # 只要用户提供了问题，或者提供了时间/地点，就进入 summary_collect 阶段
        has_enough_details = bool(problem_summary) or bool(extracted_time) or bool(extracted_location) or len(user_message) > 10
        
        if has_enough_details:
            # 进入 summary_collect 阶段收集手机号/车牌号
            phase = "summary_collect"
            # 检查是否信息完整
            missing = []
            if not phone:
                missing.append("手机号")
            if not license_plate:
                missing.append("车牌号")
            
            if not missing:
                # 信息完整，直接确认
                reply_content = f"""好的，我先整理一下信息：
手机号：{phone}
车牌号：{license_plate}
情况：{problem_summary}
请确认以上信息是否准确，准确的话回复"确认"。"""
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
            else:
                # 信息不完整，继续收集（【修复 FALL-002】使用情绪检测）
                apology_msg = _get_apology_message(user_message)
                reply_content = f"""{apology_msg}
我已经记录了您的问题：
{problem_summary}
为了进一步核实，麻烦您提供一下{"和".join(missing)}。"""
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
        
        # 还没有足够信息，继续追问
        apology_msg = _get_apology_message(user_message)
        reply_content = f"""{apology_msg}
我已经记录了您的问题：
{problem_summary if problem_summary else "正在记录中..."}
请问还能告诉我更多细节吗？比如具体发生在什么时间、什么地点？"""
        
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
    if phase == "summary_collect" or phase == "collect_info":
        # 提取用户消息中的信息（包括时间、地点）
        extracted = _extract_info_by_llm(ctx, user_message, check_complaint=False)
        extracted_phone = extracted.get("phone", "")
        extracted_plate = extracted.get("license_plate", "")
        extracted_problem = extracted.get("problem", "")
        extracted_time = extracted.get("time", "")
        extracted_location = extracted.get("location", "")
        
        # 【调试日志】
        logger.info(f"兜底流程 - 用户消息: '{user_message}'")
        logger.info(f"兜底流程 - 提取结果: phone='{extracted_phone}', plate='{extracted_plate}', problem='{extracted_problem}'")
        
        # 更新信息
        updated = []
        if extracted_phone:
            phone = extracted_phone
            updated.append(f"手机号 {phone}")
        if extracted_plate:
            license_plate = extracted_plate
            updated.append(f"车牌号 {license_plate}")
        
        # 【确定性修复】完全不使用 Summary Agent，改用简单的文本替换
        # 优先级：entry_problem > problem_summary > extracted_problem
        # 只做简单的"用户"到"您"的替换，避免 LLM 输出不稳定
        if not problem_summary:
            if entry_problem:
                # 使用 entry_problem，简单把"用户"替换成"您"
                problem_summary = entry_problem.replace("用户", "您")
                updated.append(f"情况 {problem_summary}")
            elif extracted_problem:
                # 使用 extracted_problem，简单把"用户"替换成"您"
                problem_summary = extracted_problem.replace("用户", "您")
                updated.append(f"情况 {problem_summary}")
        
        # 【新增】智能合并问题描述（时间、地点）
        if (extracted_time or extracted_location) and problem_summary:
            new_details = []
            if extracted_time:
                new_details.append(f"时间：{extracted_time}")
            if extracted_location:
                new_details.append(f"地点：{extracted_location}")
            
            if new_details:
                problem_summary = f"{problem_summary}，{'，'.join(new_details)}"
                updated.append(f"情况 {problem_summary}")
                logger.info(f"兜底流程 - 用户补充了问题细节，更新后的问题：{problem_summary}")
        
        # 检查是否有信息更新
        if updated:
            logger.info(f"兜底流程 - 更新信息: {', '.join(updated)}")
        else:
            logger.info("兜底流程 - 未提取到新信息，继续询问")
        
        # 先判断用户是否在确认
        if _is_confirm(user_message):
            logger.info("兜底流程 - 用户确认，进入确认阶段")
            phase = "confirm"
            reply_content = f"""好的，我先整理一下信息：
手机号：{phone}
车牌号：{license_plate}
情况：{problem_summary}
请确认以上信息是否准确，准确的话回复"确认"。"""
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
        
        # 收集缺失的信息
        missing = []
        if not phone:
            missing.append("手机号")
        if not license_plate:
            missing.append("车牌号")
        
        # 【优化】检查用户是否只是在回应（如只说"手机号"或"车牌"）
        is_just_responding = False
        user_msg_lower = user_message.strip().lower()
        if len(user_msg_lower) <= 10 and ("手机" in user_msg_lower or "车牌" in user_msg_lower or "号" in user_msg_lower):
            is_just_responding = True
            logger.info(f"兜底流程 - 用户只是在回应: {user_message}")
        
        # 如果有信息更新，友好告知并继续收集
        if updated:
            if missing:
                # 还有缺失信息，继续收集
                reply_content = f"""好的，记录了{"，".join(updated)}！
麻烦再提供一下您的{"和".join(missing)}好吗？"""
            else:
                # 信息完整，进入确认阶段
                phase = "confirm"
                reply_content = f"""好的，我先整理一下信息：
手机号：{phone}
车牌号：{license_plate}
情况：{problem_summary}
请确认以上信息是否准确，准确的话回复"确认"。"""
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
        elif is_just_responding:
            # 用户只是在回应，友好提示并继续收集
            if missing:
                reply_content = f"""麻烦您提供一下您的{"和".join(missing)}好吗？"""
        else:
            # 没有提取到新信息，也不是在回应，直接询问缺失信息
            if missing:
                # 【修复 FALL-002】使用情绪检测
                apology_msg = _get_apology_message(user_message)
                reply_content = f"""{apology_msg}
我已经记录了您的问题：
{problem_summary}
为了进一步核实，麻烦您提供一下{"和".join(missing)}。"""
            else:
                # 信息完整，进入确认阶段
                phase = "confirm"
                reply_content = f"""好的，我先整理一下信息：
手机号：{phone}
车牌号：{license_plate}
情况：{problem_summary}
请确认以上信息是否准确，准确的话回复"确认"。"""
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
        
        # 保持在当前阶段，继续收集
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
    
    # ==================== 确认阶段 ====================
    if phase == "confirm":
        # 【优先检查】用户是否在确认
        if _is_confirm(user_message):
            logger.info("兜底流程 - 用户确认，准备创建工单")
            # 【重要】用户确认后，直接返回，让图的条件节点处理
            reply_content = f"""✅ 收到您的问题，我们的工作人员将会尽快处理，并在1-3个工作日内联系您。
手机号：{phone}
车牌号：{license_plate}
情况：{problem_summary}"""
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
        
        # 再检查是否在取消
        if _is_cancel(user_message):
            logger.info("兜底流程 - 用户取消，退出确认阶段")
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
        
        # 提取用户可能的信息更新
        extracted = _extract_info_by_llm(ctx, user_message, check_complaint=False)
        extracted_phone = extracted.get("phone", "")
        extracted_plate = extracted.get("license_plate", "")
        extracted_problem = extracted.get("problem", "")
        extracted_time = extracted.get("time", "")
        extracted_location = extracted.get("location", "")
        
        # 更新信息
        updated = []
        if extracted_phone:
            phone = extracted_phone
            updated.append(f"手机号 {phone}")
        if extracted_plate:
            license_plate = extracted_plate
            updated.append(f"车牌号 {license_plate}")
        if extracted_problem:
            problem_summary = extracted_problem.replace("用户", "您")
            entry_problem = extracted_problem
            updated.append(f"情况 {problem_summary}")
        
        # 补充问题细节（时间、地点）
        if (extracted_time or extracted_location) and problem_summary:
            new_details = []
            if extracted_time:
                new_details.append(f"时间：{extracted_time}")
            if extracted_location:
                new_details.append(f"地点：{extracted_location}")
            
            if new_details:
                problem_summary = f"{problem_summary}，{'，'.join(new_details)}"
                updated.append(f"情况 {problem_summary}")
        elif updated:
            # 有信息更新，重新整理信息让用户确认
            reply_content = f"""好的，更新了{"，".join(updated)}！
我再整理一下信息：
手机号：{phone}
车牌号：{license_plate}
情况：{problem_summary}
请确认以上信息是否准确，准确的话回复"确认"。"""
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
        else:
            # 没有确认也没有更新，再次展示信息让用户确认
            reply_content = f"""我再整理一下信息：
手机号：{phone}
车牌号：{license_plate}
情况：{problem_summary}
请确认以上信息是否准确，准确的话回复"确认"。"""
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
    
    # ==================== 完成阶段 ====================
    if phase == "done":
        logger.info("兜底流程 - 已完成，准备清理状态")
        return FallbackOutput(
            reply_content=f"✅ 收到您的问题，我们的工作人员将会尽快处理，并在1-3个工作日内联系您。",
            fallback_phase="",
            phone="",
            license_plate="",
            problem_summary="",
            user_supplement="",
            entry_problem="",
            case_confirmed=True,
            conversation_truncate_index=0
        )
    
    # ==================== 默认 ====================
    logger.info(f"兜底流程 - 默认分支，当前phase: {phase}")
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
