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
    try:
        prompt = f"""请从用户消息中提取手机号和车牌号信息。

用户消息：{user_message}

【提取规则】
1. 手机号：11位数字，以1开头
   - 用户可能分段说出：如"139。16425678"或"139 1642 5678"
   - 请将所有数字拼接起来，提取完整的11位手机号
   
2. 车牌号：省份简称+字母+5-6位字母或数字
   - 用户可能分段说出：如"沪a Dr 3509"或"京 A 1 2 3 4 5"
   - 请将所有部分拼接，提取完整车牌号
   - 转为大写，去掉空格
   
3. 如果某项信息不存在，返回空字符串

【示例】
输入："手机号139。16425678。车牌号。沪a Dr 3509."
输出：{{"phone": "13916425678", "license_plate": "沪ADR3509"}}

输入："我的手机是1-3-9-1-2-3-4-5-6-7-8"
输出：{{"phone": "13912345678", "license_plate": ""}}

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
        
    except Exception as e:
        # LLM 调用失败或解析失败，使用正则兜底
        logger.warning(f"LLM 提取信息失败，使用正则兜底: {e}")
        return _extract_info_by_regex(user_message)


def _extract_info_by_regex(user_message: str) -> dict:
    """使用正则表达式提取手机号和车牌号（兜底方案）"""
    # 手机号正则
    phone_pattern = r'1[3-9]\d[\s\-]?\d{4}[\s\-]?\d{4}|1[3-9]\d{9}'
    phone_match = re.search(phone_pattern, user_message)
    phone = phone_match.group().replace(" ", "").replace("-", "") if phone_match else ""
    
    # 车牌号正则
    plate_pattern = r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9\s]{4,6}'
    plate_match = re.search(plate_pattern, user_message)
    license_plate = plate_match.group().replace(" ", "").upper() if plate_match else ""
    
    logger.info(f"正则提取结果 - 手机号: {phone}, 车牌号: {license_plate}")
    return {"phone": phone, "license_plate": license_plate}


def _generate_problem_summary(
    ctx,
    conversation_history: list,
    user_supplement: str,
    entry_problem: str = ""
) -> str:
    """使用 LLM 从对话历史生成问题总结
    
    Args:
        ctx: 上下文
        conversation_history: 对话历史
        user_supplement: 用户补充说明
        entry_problem: 用户进入兜底流程时的问题描述（优先使用）
    """
    
    # 如果有用户进入兜底时的问题描述，先进行智能提取
    base_problem = entry_problem if entry_problem else ""
    
    # 构建对话摘要（用于补充上下文）
    dialogue_text = ""
    if conversation_history:
        for msg in conversation_history[-10:]:  # 最近10轮对话
            role = "用户" if msg.get("role") == "user" else "客服"
            content = msg.get("content", "")
            dialogue_text += f"{role}：{content}\n"
    
    # 如果有用户补充，优先使用
    if user_supplement:
        prompt = f"""请根据以下信息，总结用户遇到的核心问题。

用户明确指出的问题：
{user_supplement}

原始问题描述：
{base_problem if base_problem else "无"}

对话上下文：
{dialogue_text if dialogue_text else "无"}

【重要规则】
1. 问题总结必须以用户明确指出的问题为准
2. 必须准确反映用户的核心问题，不能笼统描述
3. 如果用户提到"优惠券没有抵扣/没用上/没用"，总结必须是"用户遇到优惠券未抵扣问题，需要处理"
4. 不要忽略用户提到的具体问题细节
5. 简洁明了，不超过50字
6. 格式：用户遇到XXX问题，需要处理。

问题总结："""
    elif base_problem:
        prompt = f"""请根据用户的问题描述，总结核心问题。

用户问题描述：
{base_problem}

【重要规则】
1. 必须准确反映用户的核心问题，不能笼统描述
2. 如果用户提到"优惠券没有抵扣/没用上/没用"，总结必须是"用户遇到优惠券未抵扣问题，需要处理"
3. 如果用户提到"扣费错误/多扣钱"，总结必须包含"扣费"相关内容
4. 不要忽略用户提到的具体问题细节
5. 简洁明了，不超过50字
6. 格式：用户遇到XXX问题，需要处理。

问题总结："""
    elif dialogue_text:
        prompt = f"""请根据以下对话记录，准确总结用户遇到的核心问题。

对话记录：
{dialogue_text}

【重要规则】
1. 只总结用户实际遇到的问题，不要臆测
2. 如果用户提到优惠券、结算、扣款等，一定要包含在总结中
3. 不要添加用户没有提到的问题
4. 简洁明了，不超过50字

问题总结："""
    else:
        return "用户遇到充电桩相关问题，需要人工处理。"

    client = LLMClient(ctx=ctx)
    response = client.invoke(
        messages=[HumanMessage(content=prompt)],
        model="doubao-seed-1-8-251228",
        temperature=0.3,
        max_completion_tokens=200
    )
    
    # 提取响应文本
    result = ""
    if isinstance(response.content, list):
        text_parts = []
        for item in response.content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        result = " ".join(text_parts).strip()
    else:
        result = str(response.content).strip()
    
    # 【关键】验证总结是否准确（如果 entry_problem 包含关键词但结果不包含，修正）
    if base_problem:
        # 检查是否包含关键问题词汇
        if "优惠券" in base_problem and "优惠券" not in result:
            result = "用户遇到优惠券未抵扣问题，需要处理。"
        elif "扣" in base_problem and "扣" not in result and "费" not in result:
            result = "用户遇到扣费相关问题，需要处理。"
    
    # 如果结果仍然太笼统，尝试提取更准确的内容
    if result and "充电桩相关问题" in result and base_problem:
        # 重新生成，强制要求准确
        if "优惠券" in base_problem:
            result = "用户遇到优惠券未抵扣问题，需要处理。"
    
    return result


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
    # 取消关键词（在兜底流程中表达取消意图）
    cancel_keywords = [
        "取消兜底", "不要兜底", "不用处理了", "不需要人工",
        "算了", "再见", "不聊了", "不玩了", "不和你玩",
        "算了不处理", "取消处理", "不用了", "不需要了"
    ]
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
                entry_problem="",
                case_confirmed=False
            )
    
    # ==================== 阶段0：询问问题 ====================
    if phase == "" or phase == "ask_problem":
        # 先从 state 中获取已有的信息（以防用户之前已经提供了手机号/车牌号）
        phone = state.phone
        license_plate = state.license_plate
        entry_problem = state.entry_problem
        
        # 刚进入兜底流程，先询问用户具体遇到了什么问题
        if phase == "":
            # 第一次进入，询问问题
            logger.info("兜底流程 - 刚进入，先询问用户具体问题")
            reply_content = """好的，请问您具体遇到了什么问题呢？"""
            
            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase="ask_problem",
                phone=phone,
                license_plate=license_plate,
                problem_summary="",
                user_supplement="",
                entry_problem=entry_problem,
                case_confirmed=False
            )
        else:
            # 在 ask_problem 阶段，用户回复了问题描述
            # 提取用户的问题描述
            has_problem_desc = any(kw in user_message for kw in ["充", "电", "优惠券", "扣", "结算", "故障", "问题", "退款", "钱", "索赔", "起火", "烧毁", "投诉"])
            
            if has_problem_desc:
                # 用户描述了问题，记录下来，进入收集信息阶段
                entry_problem = user_message
                logger.info(f"兜底流程 - 用户描述了问题，记录并进入收集信息: {entry_problem[:50]}...")
                phase = "collect_info"
            else:
                # 用户没有描述清楚问题，继续询问
                logger.info("兜底流程 - 用户没有描述清楚问题，继续询问")
                reply_content = """不好意思，我没太听明白～麻烦您描述一下具体遇到了什么问题，比如充电故障、优惠券问题、退款问题等？"""
                
                return FallbackOutput(
                    reply_content=reply_content,
                    fallback_phase="ask_problem",
                    phone=phone,
                    license_plate=license_plate,
                    problem_summary="",
                    user_supplement="",
                    entry_problem=entry_problem,
                    case_confirmed=False
                )
    
    # ==================== 阶段1：收集信息 ====================
    if phase == "collect_info":
        phone = state.phone
        license_plate = state.license_plate
        entry_problem = state.entry_problem
        
        # 如果是第一次进入兜底流程（没有 entry_problem），记录用户当前的问题描述
        if not entry_problem:
            # 【优先使用当前用户消息】
            # 用户进入兜底流程时发送的消息通常就是问题描述
            # 检查当前消息是否包含实际问题描述
            has_problem_desc = any(kw in user_message for kw in ["充", "电", "优惠券", "扣", "结算", "故障", "问题", "退款", "钱"])
            
            # ✅ 关键修复：只要包含问题描述，即使同时包含手机号/车牌号，也要提取问题描述！
            if has_problem_desc:
                # 当前消息包含问题描述，直接使用（即使同时包含手机号/车牌号）
                entry_problem = user_message
                logger.info(f"兜底流程 - 从当前消息提取问题描述: {entry_problem[:50]}...")
            else:
                # 当前消息不包含问题描述（如纯情绪词或只有手机号/车牌号）
                # 从对话历史中找到最近的问题描述
                if state.conversation_history:
                    for msg in reversed(state.conversation_history):
                        if msg.get("role") == "user":
                            content = msg.get("content", "")
                            # 排除手机号/车牌号相关的消息
                            if "手机" in content or "车牌" in content or "联系" in content:
                                continue
                            # 排除太短的消息
                            if len(content) < 10:
                                continue
                            # 检查是否包含实际问题描述
                            if any(kw in content for kw in ["充", "电", "优惠券", "扣", "结算", "故障", "问题", "退款", "钱"]):
                                entry_problem = content
                                logger.info(f"兜底流程 - 从历史消息提取问题描述: {entry_problem[:50]}...")
                                break
                
                # 如果还是没有找到，使用默认描述
                if not entry_problem:
                    entry_problem = "用户遇到充电桩相关问题，需要人工处理。"
                    logger.info("兜底流程 - 使用默认问题描述")
            
            logger.info(f"兜底流程 - 最终记录的用户问题描述: {entry_problem[:50]}...")
        
        # 使用 LLM 从用户消息中提取信息
        extracted = _extract_info_by_llm(ctx, user_message)
        extracted_phone = extracted.get("phone", "")
        extracted_plate = extracted.get("license_plate", "")
        
        # 检测用户是否表达抱怨（如"刚才不是说了吗"）
        complaint_keywords = [
            "刚才说了", "不是说了吗", "已经告诉", "不是已经", "刚才不是", "已经说了",
            "不再重复", "不要重复", "不用再问", "你不是让我", "我不是告诉你",
            "看历史", "前面都说了", "前面已经", "之前说了", "刚才不是告诉你"
        ]
        is_complaint = any(kw in user_message for kw in complaint_keywords)
        
        if extracted_phone:
            phone = extracted_phone
        if extracted_plate:
            license_plate = extracted_plate
        
        # 检查是否已收集齐信息
        if phone and license_plate:
            # 信息齐全，生成问题总结（使用 entry_problem）
            problem_summary = _generate_problem_summary(
                ctx, state.conversation_history, "", entry_problem
            )
            logger.info(f"兜底流程 - 信息收集完成，生成问题总结: {problem_summary[:50]}...")
            
            reply_content = f"""好的，信息已记录：

📱 手机号：{phone}
🚗 车牌号：{license_plate}

───────────
**问题总结：**
{problem_summary}

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
                case_confirmed=False
            )
        
        # 如果用户表达了抱怨，但信息仍不完整，先道歉再继续收集
        if is_complaint:
            if not phone and not license_plate:
                reply_content = f"""抱歉抱歉！可能是我这边网络问题没收到...

麻烦您再报一次手机号和车牌号吧～"""
            elif not phone:
                reply_content = f"""抱歉抱歉！可能是我这边网络问题没收到手机号...

麻烦您再报一次吧～"""
            else:
                reply_content = f"""抱歉抱歉！可能是我这边网络问题没收到车牌号...

麻烦您再报一次吧～"""
            
            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase="collect_info",
                phone=phone,
                license_plate=license_plate,
                problem_summary="",
                user_supplement="",
                entry_problem=entry_problem,
                case_confirmed=False
            )
        
        # 信息不齐全，继续收集
        if not phone and not license_plate:
            reply_content = """好的，我会帮您记录并反馈给工作人员处理～

方便提供一下您的手机号和车牌号吗？这样工作人员可以联系您处理问题。

您可以直接说，比如："手机13912345678，车牌京A12345" """
        
        elif not phone:
            reply_content = f"""好的，车牌号 {license_plate} 已记下！

方便再提供一下您的手机号吗？ """
        
        else:
            reply_content = f"""好的，手机号 {phone} 已记下！

方便再提供一下您的车牌号吗？ """
        
        return FallbackOutput(
            reply_content=reply_content,
            fallback_phase="collect_info",
            phone=phone,
            license_plate=license_plate,
            problem_summary="",
            user_supplement="",
            entry_problem=entry_problem,
            case_confirmed=False
        )
    
    # ==================== 阶段2：用户确认 ====================
    elif phase == "confirm":
        phone = state.phone
        license_plate = state.license_plate
        problem_summary = state.problem_summary
        user_supplement = state.user_supplement
        entry_problem = state.entry_problem
        
        # 清理用户消息（去掉标点符号，用于模糊匹配）
        import string
        cleaned_message = user_message.strip()
        # 去掉中文和英文标点
        for char in "，。！？、；：""''！？.,;:!?":
            cleaned_message = cleaned_message.replace(char, "")
        
        # 检查用户是否确认（支持"确认。"、"确认了"、"是"、"对的"等）
        confirm_keywords = [
            "确认", "确认无误", "没问题", "是的", "对", "好的", "正确", "没错", 
            "准确", "可以", "行", "OK", "ok", "嗯", "是的的", "对的",
            "没其他问题", "没其他问题了", "没有其他问题", "没有其他问题了",
            "没事了", "没问题了", "就这样", "可以了", "行了", "好的没问题",
            "确认了", "确认呀", "是对的", "是对", "是", "对呀", "好", "嗯嗯"
        ]
        # 模糊匹配：检查清理后的消息是否等于或在关键词列表中
        is_confirm = cleaned_message in confirm_keywords or any(
            cleaned_message.startswith(kw) or cleaned_message == kw for kw in confirm_keywords
        )
        
        if is_confirm:
            logger.info(f"兜底流程 - 用户确认完成 (原始消息: {user_message}, 清理后: {cleaned_message})")
            
            # 整合用户补充内容
            final_summary = problem_summary
            if user_supplement:
                final_summary = f"{problem_summary}\n\n用户补充：{user_supplement}"
            
            reply_content = """✅ 收到您的问题，我们的工作人员将会尽快处理，并在1-3个工作日内联系您。

如有其他问题，随时可以问我。"""
            
            return FallbackOutput(
                reply_content=reply_content,
                fallback_phase="done",
                phone=phone,
                license_plate=license_plate,
                problem_summary=final_summary,
                user_supplement=user_supplement,
                entry_problem=entry_problem,
                case_confirmed=True
            )
        
        # 用户有补充内容或纠正
        logger.info(f"兜底流程 - 用户补充/纠正: {user_message}")
        
        # 检测用户是否在纠正问题总结
        correction_keywords = ["不对", "错了", "不对嘛", "搞错了", "根本就不对", "忽略", "漏掉", "没说", "没提到", "不是这个", "我的问题是"]
        is_correction = any(kw in user_message for kw in correction_keywords)
        
        if is_correction:
            # 用户纠正，重新生成问题总结，以用户的纠正为准
            user_supplement = user_message
            new_summary = _generate_problem_summary(
                ctx, state.conversation_history, user_message, entry_problem
            )
        else:
            # 用户补充，追加到补充内容
            user_supplement = f"{user_supplement}\n{user_message}" if user_supplement else user_message
            # 重新生成问题总结
            new_summary = _generate_problem_summary(
                ctx, state.conversation_history, user_supplement, entry_problem
            )
        
        reply_content = f"""好的，已更新问题总结：

───────────
**问题总结：**
{new_summary}

───────────
以上信息准确吗？准确的话回复"确认"，还需要补充的话请继续说～"""
        
        return FallbackOutput(
            reply_content=reply_content,
            fallback_phase="confirm",
            phone=phone,
            license_plate=license_plate,
            problem_summary=new_summary,
            user_supplement=user_supplement,
            entry_problem=entry_problem,
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
            entry_problem=state.entry_problem,
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
        entry_problem="",
        case_confirmed=False
    )
