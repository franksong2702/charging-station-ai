"""
兜底流程节点 - 动态判断版本

核心原则：
1. 用 LLM 判断问题描述是否明确，不是数轮数
2. 明确（包含地点 + 问题现象）：直接收集手机号和车牌号
3. 不明确（只有我要投诉/有问题）：追问具体问题
4. 信息完整后：生成总结，请求用户确认
5. 用户确认后：创建工单 + 发送邮件
"""
import os
import json
import logging
import re

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from tools.llm import create_llm_client
from langchain_core.messages import SystemMessage, HumanMessage

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


def _is_problem_clear(ctx: Context, problem_text: str) -> bool:
    """
    用 LLM 判断问题描述是否明确
    
    判断标准：
    - 明确：包含「地点 + 问题现象」
    - 不明确：只有「我要投诉/有问题」
    """
    prompt = """你是一个专业的充电桩客服问题判断专家。

【任务】
判断用户的问题描述是否明确，能否直接创建工单。

【判断标准】
✅ 明确（返回 true）：
- 包含具体地点（如：徐汇滨江、哪个充电站、哪个平台等）
- 包含具体问题现象（如：充不进去、扣了钱、充电桩坏了等）
- 两个条件都满足

❌ 不明确（返回 false）：
- 只有"我要投诉"、"有问题"、"帮我处理"等空泛表达
- 缺少地点或缺少问题现象
- 任何一个条件不满足

【用户问题】
{{problem_text}}

【输出格式】
仅返回 JSON 格式：
{
    "is_clear": true/false,
    "reason": "简要说明原因"
}

【示例】
问题："我要投诉" → {"is_clear": false, "reason": "只有投诉意图，缺少地点和问题现象"}
问题："充不进去电" → {"is_clear": false, "reason": "有问题现象，但缺少地点"}
问题："徐汇滨江充电站充不进去电" → {"is_clear": true, "reason": "有地点（徐汇滨江充电站）和问题现象（充不进去电）"}
问题："什么破系统，扣了我50块" → {"is_clear": false, "reason": "有情绪和问题现象，但缺少地点"}
问题："万达充电站扣了钱没充上" → {"is_clear": true, "reason": "有地点（万达充电站）和问题现象（扣了钱没充上）"}"""

    try:
        client = create_llm_client(ctx=ctx, provider="doubao")
        response = client.invoke(
            messages=[
                SystemMessage(content=prompt),
                HumanMessage(content=f"用户问题：{problem_text}")
            ],
            model="doubao-seed-1-8-251228",
            temperature=0.1,
            max_completion_tokens=200
        )

        content = str(response.content).strip()
        if content.startswith("```"):
            content = re.sub(r'^```json?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)

        result = json.loads(content)
        is_clear = result.get("is_clear", False)
        
        logger.info(f"问题明确度判断 - 问题: {problem_text}, 结果: {is_clear}, 原因: {result.get('reason', '')}")
        
        return is_clear

    except Exception as e:
        logger.error(f"问题明确度判断失败: {e}")
        # 如果 LLM 调用失败，保守判断为不明确
        return False


def fallback_node(state: FallbackInput, config: RunnableConfig, runtime: Runtime[Context]) -> FallbackOutput:
    """
    title: 兜底流程处理 - 动态判断问题明确度
    desc: 用 LLM 判断问题是否明确，明确时直接收集信息，不明确时追问详情
    """
    ctx = runtime.context

    # 从状态中获取当前信息
    user_message = state.user_message.strip()
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

    # 先判断问题是否明确，再检查确认词
    # 整合问题信息（用于 LLM 判断）
    problem_for_judge = entry_problem or user_message
    
    # 如果 entry_problem 很简短（只有"我要投诉"、"有问题"等），且当前 user_message 更具体，优先用当前 user_message
    if entry_problem and len(entry_problem) < 15 and len(user_message) > len(entry_problem):
        # 检查 entry_problem 是否是空泛的表达
        vague_keywords = ["我要投诉", "有问题", "帮我处理", "投诉", "处理一下", "帮我"]
        is_vague = any(keyword in entry_problem for keyword in vague_keywords)
        
        if is_vague:
            # entry_problem 是空泛的，用当前更具体的 user_message
            problem_for_judge = user_message
            # 同时更新 entry_problem，避免下一轮又回到空泛的判断
            entry_problem = user_message
            problem_summary = user_message.replace("用户", "您")
    
    if problem_summary and problem_summary != entry_problem:
        problem_for_judge = problem_summary

    # 判断问题是否明确
    is_clear = _is_problem_clear(ctx, problem_for_judge)
    
    # 检查确认词 - 只有问题明确时才检查
    if is_clear and _is_confirm(user_message):
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

    # ============================================
    # 根据 is_clear 判断后续流程
    # ============================================

    if is_clear:
        # 问题明确：直接收集手机号和车牌号
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
            phone=phone,
            license_plate=license_plate,
            problem_summary=problem_summary or entry_problem,
            user_supplement="",
            entry_problem=entry_problem,  # 确保返回更新后的 entry_problem
            case_confirmed=False,
            conversation_truncate_index=conversation_truncate_index
        )
    else:
        # 问题不明确：追问详情，同时更新 entry_problem
        # 将用户的补充信息合并到 entry_problem
        if user_message and len(user_message) >= 2:
            # 检查 entry_problem 是否在第 168-178 行已经更新过
            # 如果 entry_problem 等于 user_message，说明已经在第 177 行更新过了，不需要再追加
            if entry_problem and entry_problem != user_message and len(entry_problem) >= 2:
                # 已有 entry_problem，且不是刚更新的，追加新信息
                entry_problem = f"{entry_problem} {user_message}"
            elif not entry_problem or len(entry_problem) < 2:
                # 没有 entry_problem 或 entry_problem 太短，使用当前 user_message
                entry_problem = user_message
            # 同步更新 problem_summary
            problem_summary = entry_problem.replace("用户", "您")
        
        reply_content = _generate_followup_question(entry_problem, user_message)
        return FallbackOutput(
            reply_content=reply_content,
            fallback_phase="asking_details",
            phone=phone,
            license_plate=license_plate,
            problem_summary=problem_summary or entry_problem,
            user_supplement="",
            entry_problem=entry_problem,  # 返回更新后的 entry_problem
            case_confirmed=False,
            conversation_truncate_index=conversation_truncate_index
        )


def _generate_followup_question(entry_problem: str, user_message: str) -> str:
    """生成追问问题（问题不明确时使用）"""
    
    # 检查是否已经有地点相关信息（扩展关键词）
    has_location = any(keyword in entry_problem for keyword in [
        "地点", "哪个", "哪里", "充电站", "小程序", "平台", "站", "园", "点", "app", "APP"
    ])
    
    # 检查是否已经有问题现象相关信息
    has_problem = any(keyword in entry_problem for keyword in [
        "充", "扣", "坏", "问题", "故障", "不行", "没用", "退款", "投诉"
    ])
    
    # 如果用户已经说了一些内容，针对性追问
    if entry_problem and len(entry_problem) > 5:
        if not has_location:
            # 还没有地点信息，追问地点
            return "好的，请问您是在哪个充电站或者平台遇到的这个问题呢？大概是什么时间？"
        elif not has_problem:
            # 已有地点，但还没有具体问题现象，追问问题
            return "明白了。请问您具体遇到了什么问题呢？是充不进去电、扣费有问题，还是其他情况？"
        else:
            # 已有地点和问题，让用户补充更多细节或确认
            return "好的，情况我了解了。请问还有其他需要补充的信息吗？或者您可以告诉我手机号和车牌号，我来帮您创建工单。"
    
    # 通用追问
    return "好的，请问您具体遇到了什么情况？能详细说说吗？比如是在哪个平台充电的、什么时候、在哪里、遇到了什么问题？"
