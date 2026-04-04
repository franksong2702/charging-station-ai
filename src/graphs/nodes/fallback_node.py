"""
兜底流程节点 - 处理需要人工介入的场景
支持多轮确认：用户说什么就记什么，要改什么就改什么，最后确认

优化点：
1. 不再死板地按顺序收集信息（先手机号、后车牌号）
2. 用户说什么就记什么（手机号/车牌号/问题描述，随意顺序）
3. 用户要改什么就直接改，不用从头开始
4. 最后让用户确认所有信息即可
"""
import os
import json
import logging
import re

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
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
1. 手机号：以1开头的数字串
   - 即使位数不对（如少了或多了一位），也要提取出来
   - 用户可能分段说出：如"139。16425678"或"139 1642 5678"
   - 请将所有数字拼接起来
   
2. 车牌号：省份简称+字母+数字/字母
   - 用户可能分段说出：如"沪a Dr 3509"或"沪 A 1 2 3 4 5"
   - 请将所有部分拼接，提取完整车牌号
   - 转为大写，去掉空格
   
3. 问题描述：用户描述的具体问题
   - 例如："充电桩坏了"、"优惠券没用"、"扣费错误"等

【输出格式】
请返回JSON格式：
{{"phone": "手机号（即使位数不对也要返回）", "license_plate": "车牌号", "problem": "问题描述"}}

如果某项信息不存在，返回空字符串""。

请直接返回JSON格式，不要其他说明："""

        client = LLMClient(ctx=ctx)
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
        
        # 验证手机号格式（必须是11位）
        if phone and len(re.sub(r'\D', '', phone)) == 11:
            phone = re.sub(r'\D', '', phone)
        else:
            phone = ""
            logger.warning(f"手机号格式错误（非11位）：{phone}")
        
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
    desc: 简单直接：用户说什么就记什么，要改什么就改什么，最后确认
    integrations: 大语言模型
    """
    ctx = runtime.context
    user_message = state.user_message.strip()
    phase = state.fallback_phase or "collect_info"
    
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
        phase = "collect_info"
    
    # ==================== 收集/更新信息阶段 ====================
    if phase == "collect_info" or phase == "" or phase == "ask_problem":
        # 提取用户消息中的信息
        extracted = _extract_info_by_llm(ctx, user_message, check_complaint=False)
        extracted_phone = extracted.get("phone", "")
        extracted_plate = extracted.get("license_plate", "")
        extracted_problem = extracted.get("problem", "")
        
        # 用正则直接从用户消息中提取手机号（不管 LLM 返回什么）
        phone_raw = ""
        phone_valid = False
        phone = ""
        
        # 提取用户消息中的所有数字串
        all_numbers = re.findall(r'\d+', user_message)
        for num_str in all_numbers:
            if len(num_str) == 11 and num_str.startswith('1'):
                phone = num_str
                phone_valid = True
                phone_raw = num_str
                logger.info(f"从用户消息中提取到11位手机号: {phone}")
                break
            elif len(num_str) >= 10 and len(num_str) <= 12 and num_str.startswith('1'):
                phone_raw = num_str
                logger.info(f"从用户消息中提取到疑似手机号（{len(num_str)}位）: {phone_raw}")
                break
            elif 8 <= len(num_str) <= 13 and num_str.startswith('1'):
                # 可能是被截断的手机号，保留原始值用于友好提示
                if not phone_raw:
                    phone_raw = num_str
                    logger.info(f"从用户消息中提取到疑似手机号（{len(num_str)}位）: {phone_raw}")
        
        # LLM 提取车牌号和问题描述
        extracted_plate = extracted.get("license_plate", "")
        extracted_problem = extracted.get("problem", "")
        
        # 检查车牌号（只要提供了就记录）
        license_plate = extracted_plate.replace(" ", "").upper() if extracted_plate else ""
        
        # 更新信息
        updated = []
        if phone_valid:
            updated.append(f"手机号 {phone}")
        if extracted_plate:
            updated.append(f"车牌号 {license_plate}")
        if extracted_problem:
            problem_summary = extracted_problem
            updated.append(f"问题 {problem_summary}")
        
        # 哪些信息没识别到
        not_recognized = []
        if not phone_valid and phone_raw:
            not_recognized.append("手机号")
        if not extracted_plate:
            not_recognized.append("车牌号")
        if not extracted_problem:
            not_recognized.append("问题描述")
        
        # 检查是否有信息更新
        if updated:
            logger.info(f"兜底流程 - 更新信息: {', '.join(updated)}")
        
        # 生成友好提示
        hints = []
        if not_recognized:
            if "手机号" in not_recognized and phone_raw:
                phone_digits = re.sub(r'\D', '', phone_raw)
                if len(phone_digits) > 0 and len(phone_digits) < 11:
                    hints.append(f"手机号位数不够，请补全（当前{len(phone_digits)}位）")
                elif len(phone_digits) > 11:
                    hints.append(f"手机号位数多了，请检查")
                else:
                    hints.append("手机号没识别到，请重新说一下")
            if "车牌号" in not_recognized:
                hints.append("车牌号没识别到")
            if "问题描述" in not_recognized:
                hints.append("问题描述没识别到")
                hints.append("问题描述没识别到")
        
        # 检查是否需要让用户确认（已收集到足够信息）
        if phone and license_plate and problem_summary:
            # 信息齐全，让用户确认
            reply_content = f"""好的，已记录：

📱 手机号：{phone}
🚗 车牌号：{license_plate}
📝 问题：{problem_summary}

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
        if not problem_summary:
            missing.append("问题描述")
        
        # 首次进入，友好询问
        if not phone and not license_plate and not problem_summary and phase == "":
            reply_content = """好的，我来帮您记录问题反馈给工作人员～

方便告诉我：
- 📱 您的手机号
- 🚗 您的车牌号
- 📝 遇到的问题

可以直接一起说，比如："手机13812345678，车牌沪A12345，充电桩坏了" """
            
            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase="collect_info",
                phone=phone,
                license_plate=license_plate,
                problem_summary=problem_summary,
                user_supplement="",
                entry_problem=entry_problem,
                case_confirmed=False,
                conversation_truncate_index=conversation_truncate_index
            )
        
        # 已有部分信息，友好询问还缺什么
        missing_text = "、".join(missing)
        
        # 友好提示
        hint_text = ""
        if hints:
            hint_text = "\n\n" + "\n".join(hints)
        
        reply_content = f"""好的，{', '.join(updated) if updated else '收到'}～

还缺：{missing_text}{hint_text}

方便的话直接告诉我，比如："手机13812345678" 或 "车牌沪A12345" """
        
        return FallbackOutput(
            reply_content=reply_content,
            fallback_phase="collect_info",
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
    
    # 默认处理
    return FallbackOutput(
        reply_content="好的，请继续告诉我相关信息～",
        fallback_phase="collect_info",
        phone=phone,
        license_plate=license_plate,
        problem_summary=problem_summary,
        user_supplement="",
        entry_problem=entry_problem,
        case_confirmed=False,
        conversation_truncate_index=conversation_truncate_index
    )
