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


def _extract_info_by_llm(ctx: Context, user_message: str, check_complaint: bool = False) -> dict:
    """
    使用 LLM 从用户消息中提取手机号、车牌号、问题描述
    :param ctx: 运行上下文
    :param user_message: 用户消息
    :param check_complaint: 是否检测抱怨，如果是则自动生成道歉话术
    :return: 包含 phone, license_plate, problem, extra_apology 的字典
    """
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
    
    # 记录截断索引（如果还没有记录）
    if conversation_truncate_index == 0:
        conversation_truncate_index = len(conversation_history)
        logger.info(f"兜底流程 - 记录对话截断索引: {conversation_truncate_index}")
    
    logger.info(f"兜底流程 - 当前阶段: {phase}, 手机号: {phone}, 车牌号: {license_plate}")
    
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
    
    # ==================== 澄清安抚阶段 ====================
    if phase == "clarify":
        # 1. 先提取用户可能提供的手机号、车牌号、问题信息
        extracted = _extract_info_by_llm(ctx, user_message, check_complaint=False)
        extracted_phone = extracted.get("phone", "")
        extracted_plate = extracted.get("license_plate", "")
        extracted_problem = extracted.get("problem", "")
        
        # 2. 更新手机号和车牌号
        if extracted_phone:
            phone = extracted_phone
        if extracted_plate:
            license_plate = extracted_plate
        
        # 3. 【修复 P2】用 LLM 判断问题是否足够具体
        # 只有当问题足够具体时，才进入 summary_collect 阶段
        llm_client = create_llm_client(ctx)
        judge_prompt = f"""判断用户的问题描述是否足够具体，可以进入工单处理流程。

用户问题："{user_message}"

判断标准：
- 问题足够具体（有明确的故障现象、操作、问题点）：返回 "specific"
- 问题不够具体（太模糊、不完整、只是情绪表达）：返回 "vague"

只返回 "specific" 或 "vague"，不要有其他文字。"""
        
        try:
            judge_response = llm_client.invoke([HumanMessage(content=judge_prompt)])
            judge_result = judge_response.content.strip().lower()
            logger.info(f"兜底流程 - 问题具体性判断结果: {judge_result}")
        except Exception as e:
            logger.error(f"兜底流程 - 问题具体性判断失败: {e}")
            judge_result = "vague"
        
        # 4. 如果问题足够具体，设置 entry_problem 并进入 summary_collect
        if judge_result == "specific" or extracted_problem:
            # 【重要】优先使用用户当前消息作为 entry_problem
            entry_problem = extracted_problem if extracted_problem else user_message
            phase = "summary_collect"
            
            # 【确定性修复】直接设置 problem_summary，不使用 Summary Agent
            # 简单做"用户"到"您"的替换
            problem_summary = entry_problem.replace("用户", "您")
            
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
请确认以上信息是否准确，准确的话回复\"确认\"。"""
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
                # 信息不完整，继续收集
                reply_content = f"""好的，情况我了解了！
为了帮您更好地处理问题，方便提供一下您的{"和".join(missing)}吗？"""
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
        
        # 用户还没说清楚问题，先安抚并引导
        # 特别针对"退款"类诉求，先问清楚是想了解规则还是有具体订单
        if "退款" in user_message or "退钱" in user_message:
            reply_content = """您好！请问您是想了解退款规则，还是有具体的订单需要退款呢？

如果是想了解规则，我可以直接告诉您；如果是有具体订单需要处理，我来帮您登记反馈～"""
        else:
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
        # 提取用户消息中的信息（包括时间、地点）
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
        
        # 收集缺失的信息
        missing = []
        if not phone:
            missing.append("手机号")
        if not license_plate:
            missing.append("车牌号")
        
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
请确认以上信息是否准确，准确的话回复\"确认\"。"""
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
            # 没有信息更新，友好询问
            if missing:
                reply_content = f"""方便提供一下您的{"和".join(missing)}吗？"""
            else:
                # 信息完整，进入确认阶段
                phase = "confirm"
                reply_content = f"""好的，我先整理一下信息：
手机号：{phone}
车牌号：{license_plate}
情况：{problem_summary}
请确认以上信息是否准确，准确的话回复\"确认\"。"""
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
    
    # ==================== 确认阶段 - 修复 P4 ====================
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
        
        # 【修复 P4】用户没有确认，可能是在补充信息
        # 调用 LLM 提取新信息
        extracted = _extract_info_by_llm(ctx, user_message, check_complaint=False)
        extracted_phone = extracted.get("phone", "")
        extracted_plate = extracted.get("license_plate", "")
        extracted_problem = extracted.get("problem", "")
        
        updated = []
        # 更新信息
        if extracted_phone:
            phone = extracted_phone
            updated.append(f"手机号 {phone}")
        if extracted_plate:
            license_plate = extracted_plate
            updated.append(f"车牌号 {license_plate}")
        if extracted_problem:
            # 【重要】用户补充了新的问题信息，更新问题总结
            if problem_summary:
                problem_summary = f"{problem_summary}，{extracted_problem}"
            else:
                problem_summary = extracted_problem
            updated.append(f"情况 {problem_summary}")
        
        # 如果有信息更新，重新进入 summary_collect 阶段，然后再确认
        if updated:
            logger.info(f"兜底流程 - 用户在确认阶段补充信息: {', '.join(updated)}")
            # 重新收集，然后再确认
            phase = "summary_collect"
        else:
            # 没有信息更新，友好提示
            reply_content = "收到～请确认以上信息是否准确，准确的话回复\"确认\"。"
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
    
    # ==================== 默认：进入澄清安抚阶段 ====================
    # 如果没有设置 entry_problem，设置为当前用户消息（排除手机号/车牌号相关）
    if not entry_problem:
        # 简单判断：如果消息包含"手机"或"车牌"，可能是在提供信息而不是问题描述
        if "手机" in user_message or "车牌" in user_message or len(user_message) < 5:
            # 太短或只是在提供信息，进入澄清阶段
            phase = "clarify"
            reply_content = """非常抱歉给您带来了不好的体验！

您能跟我说说具体遇到了什么情况吗？我先帮您看看～"""
        else:
            # 有明确问题描述，设置 entry_problem 并进入 summary_collect
            entry_problem = user_message
            phase = "summary_collect"
            # 【确定性修复】直接设置 problem_summary，简单做"用户"到"您"的替换
            problem_summary = entry_problem.replace("用户", "您")
            reply_content = f"""好的，情况我了解了！
为了帮您更好地处理问题，方便提供一下您的手机号和车牌号吗？"""
    
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
