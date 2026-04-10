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


def _extract_info_by_llm(
    ctx,
    user_message: str,
    check_complaint: bool = False
) -> dict:
    """
    使用 LLM 从文本中提取手机号、车牌号、问题描述、时间、地点
    
    Args:
        ctx: 上下文
        user_message: 用户消息
        check_complaint: 是否检查用户是否在抱怨
        
    Returns:
        {"phone": "手机号", "license_plate": "车牌号", "problem": "问题描述", 
         "time": "时间信息", "location": "地点信息",
         "is_complaint": bool, "complaint_reason": str}
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

4. 时间信息：用户提到的时间
   - 例如："上周五"、"昨天晚上"、"今天下午3点"、"4月5日"等
   - 提取用户明确提到的时间信息

5. 地点信息：用户提到的地点
   - 例如："徐汇滨江"、"虹桥站"、"浦东机场"、"某某充电站"等
   - 提取用户明确提到的地点信息

6. 抱怨判断：判断用户是否在抱怨或不满（仅当check_complaint=true时）
   - 例如："刚才不是说了吗"、"不是已经告诉过了"、"不要再问了"等

【输出格式】
请返回JSON格式：
{{"phone": "手机号", "license_plate": "车牌号", "problem": "问题描述", "time": "时间信息", "location": "地点信息", "is_complaint": true/false, "complaint_reason": "如果抱怨，说明原因"}}

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
        time = str(result.get("time", "")).strip()
        location = str(result.get("location", "")).strip()
        
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
        
        logger.info(f"LLM 提取结果 - 手机号: {phone}, 车牌号: {license_plate}, 问题: {problem[:30] if problem else ''}, 时间: {time}, 地点: {location}, 抱怨: {is_complaint}")
        return {
            "phone": phone, 
            "license_plate": license_plate,
            "problem": problem,
            "time": time,
            "location": location,
            "is_complaint": is_complaint,
            "complaint_reason": complaint_reason
        }
        
    except Exception as e:
        logger.error(f"LLM 提取信息失败: {e}")
        return {
            "phone": "",
            "license_plate": "",
            "problem": "",
            "time": "",
            "location": "",
            "is_complaint": False,
            "complaint_reason": ""
        }


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
        for kw in confirm_keywords:
            if rest == kw:
                # 这是否定词，如"不对"、"不行"
                return False
    
    # 正常匹配确认词
    for kw in confirm_keywords:
        if kw in msg:
            return True
    return False


def _is_cancel(user_message: str) -> bool:
    """判断用户是否要取消 - 更严格的判断（修复 P2）"""
    # 只匹配明确的取消，去掉"算了"（容易误判，如"充不进去电就算了"不是要取消）
    cancel_keywords = ["取消", "不要了", "不用处理", "不需要", "不聊了", "再见"]
    # 【重要】必须完整匹配，不要部分匹配
    msg = user_message.lower().strip()
    for kw in cancel_keywords:
        if msg == kw or msg.startswith(kw + "，") or msg.startswith(kw + "。"):
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
    
    # ==================== 取消机制 - 修复 P2 ====================
    cancel_triggered = _is_cancel(user_message)
    
    # 【新增】如果当前是 clarify 阶段，且用户消息包含强烈情绪词，即使有取消词也不取消
    if cancel_triggered and phase == "clarify":
        strong_emotion_words = ["投诉", "垃圾", "气死", "太烂", "太差", "垃圾服务", "什么垃圾"]
        if any(word in user_message for word in strong_emotion_words):
            logger.info("兜底流程 - 用户情绪激动，不取消，继续澄清")
            cancel_triggered = False  # 强制不取消
    
    if cancel_triggered:
        # 真的要取消
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
    
    # ==================== 澄清安抚阶段 - 修复 P3 ====================
    if phase == "clarify":
        # 先提取信息（提取手机号、车牌、问题、时间、地点）
        extracted = _extract_info_by_llm(ctx, user_message, check_complaint=True)
        extracted_phone = extracted.get("phone", "")
        extracted_plate = extracted.get("license_plate", "")
        extracted_problem = extracted.get("problem", "")
        extracted_time = extracted.get("time", "")
        extracted_location = extracted.get("location", "")
        
        # 更新信息
        if extracted_phone:
            phone = extracted_phone
        if extracted_plate:
            license_plate = extracted_plate
        
        # 【新增】智能合并问题描述（问题、时间、地点）
        current_problem = problem_summary or entry_problem
        new_details = []
        
        if extracted_problem and extracted_problem != current_problem:
            new_details.append(extracted_problem)
        if extracted_time:
            new_details.append(f"时间：{extracted_time}")
        if extracted_location:
            new_details.append(f"地点：{extracted_location}")
        
        # 如果有新的细节，合并到问题描述中
        if new_details:
            if current_problem:
                current_problem = f"{current_problem}，{'，'.join(new_details)}"
            else:
                current_problem = '，'.join(new_details)
            problem_summary = current_problem
            logger.info(f"兜底流程 - 用户补充了问题细节，更新后的问题：{current_problem}")
        
        # 【修复 P3】如果用户提供了手机号或车牌号，但没有提供问题描述
        if (extracted_phone or extracted_plate) and not problem_summary and not entry_problem:
            # 记录用户提供的联系信息，继续问问题描述
            reply_content = f"""好的，已记录：
📱 手机号：{phone or '未提供'}
🚗 车牌号：{license_plate or '未提供'}

您能跟我说说具体遇到了什么情况吗？"""
            
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
        
        # 如果用户已经说了问题，先进一步追问更多细节（如果问题不够具体）
        if problem_summary or entry_problem:
            # 【优化】用大语言模型判断问题是否足够具体（现在问题、时间、地点）
            try:
                need_more_details_prompt = f"""请判断用户的问题描述是否足够具体，是否需要进一步追问更多细节。

用户的问题描述：{current_problem}

【判断规则】
- 如果问题描述比较模糊（只有"充不进去电"、"多扣钱"等简单描述）→ 需要更多细节
- 如果问题描述包含时间、地点、具体情况等信息 → 不需要更多细节

【输出格式】
请直接返回 JSON 格式：
{{"need_more_details": true/false}}

请直接返回 JSON 格式，不要其他说明："""
                
                client = create_llm_client(ctx=ctx, provider="doubao")
                response = client.invoke(
                    messages=[HumanMessage(content=need_more_details_prompt)],
                    model="doubao-seed-1-8-251228",
                    temperature=0.1,
                    max_completion_tokens=50
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
                need_more_details = result.get("need_more_details", True)
                logger.info(f"LLM 判断是否需要更多细节：{need_more_details}")
                
            except Exception as e:
                logger.error(f"LLM 判断问题是否具体失败：{e}")
                # 降级：默认需要更多细节
                need_more_details = True
            
            if need_more_details:
                # 【优化】智能判断已收集的信息，只追问缺失的
                # 检查问题描述中是否已有时间、地点
                has_time = "时间：" in current_problem or extracted_time
                has_location = "地点：" in current_problem or extracted_location
                
                # 构建追问列表
                questions = []
                if not has_time:
                    questions.append("什么时候发生的？")
                if not has_location:
                    questions.append("在哪个站点？")
                # 总是可以追问更具体的情况
                questions.append("具体是什么情况？")
                
                # 只有在有需要追问的问题时才追问
                if questions:
                    reply_content = f"""哦，明白了！您说的是：{current_problem}

为了更好地帮您处理，能再跟我说一说具体情况吗？比如：
"""
                    for q in questions:
                        reply_content += f"- {q}\n"
                    
                    return FallbackOutput(
                        reply_content=reply_content,
                        fallback_phase="clarify",
                        phone=phone,
                        license_plate=license_plate,
                        problem_summary=current_problem,
                        user_supplement="",
                        entry_problem=entry_problem or current_problem,
                        case_confirmed=False,
                        conversation_truncate_index=conversation_truncate_index
                    )
                else:
                    # 已经有足够信息了，直接进入收集手机号和车牌号阶段
                    reply_content = f"""哦，那我明白了，您的问题大概是这样的：{current_problem}

您的问题我们会反馈给专业的客服团队去处理。请您留下手机号和车牌号，方便我们的客服后续联系您。"""
                    return FallbackOutput(
                        reply_content=reply_content,
                        fallback_phase="summary_collect",
                        phone=phone,
                        license_plate=license_plate,
                        problem_summary=current_problem,
                        user_supplement="",
                        entry_problem=entry_problem or current_problem,
                        case_confirmed=False,
                        conversation_truncate_index=conversation_truncate_index
                    )
            else:
                # 问题已经比较具体了，进入收集手机号和车牌号阶段
                reply_content = f"""哦，那我明白了，您的问题大概是这样的：{current_problem}

您的问题我们会反馈给专业的客服团队去处理。请您留下手机号和车牌号，方便我们的客服后续联系您。"""
                return FallbackOutput(
                    reply_content=reply_content,
                    fallback_phase="summary_collect",
                    phone=phone,
                    license_plate=license_plate,
                    problem_summary=current_problem,
                    user_supplement="",
                    entry_problem=entry_problem or current_problem,
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
        
        # 【新增】智能合并问题描述（问题、时间、地点）
        if extracted_problem or extracted_time or extracted_location:
            current_problem = problem_summary
            new_details = []
            if extracted_problem and extracted_problem != current_problem:
                new_details.append(extracted_problem)
            if extracted_time:
                new_details.append(f"时间：{extracted_time}")
            if extracted_location:
                new_details.append(f"地点：{extracted_location}")
            
            if new_details:
                if current_problem:
                    current_problem = f"{current_problem}，{'，'.join(new_details)}"
                else:
                    current_problem = '，'.join(new_details)
                problem_summary = current_problem
                updated.append(f"情况 {problem_summary}")
                logger.info(f"兜底流程 - 用户补充了问题细节，更新后的问题：{current_problem}")
        
        # 检查是否有信息更新
        if updated:
            logger.info(f"兜底流程 - 更新信息: {', '.join(updated)}")
        else:
            logger.info("兜底流程 - 未提取到新信息，继续询问")
        
        # 检查是否需要让用户确认（已收集到手机号和车牌号）
        if phone and license_plate:
            # 【新增】调用 Summary Agent 生成详细问题总结
            try:
                summary_input = SummaryInput(
                    conversation_history=state.conversation_history
                )
                summary_output = summary_agent_node(
                    state=summary_input,
                    config=config,
                    runtime=runtime
                )
                problem_summary = summary_output.detailed_summary
                logger.info(f"Summary Agent 生成的详细总结：{problem_summary}")
            except Exception as e:
                logger.error(f"Summary Agent 调用失败：{e}")
                # 降级：使用原有逻辑
                problem_summary = problem_summary or state.problem_summary
            
            # 信息齐全，让用户确认 - 修复：将 problem_summary 中的"用户"替换为"您"
            # 因为 problem_summary 是 Summary Agent 生成的，可能包含"用户"，但这是直接对用户说的话
            problem_summary_for_user = problem_summary.replace("用户", "您") if problem_summary else ""
            reply_content = f"""好的，已记录：

📱 手机号：{phone}
🚗 车牌号：{license_plate}
📝 情况：{problem_summary_for_user}

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
    
    # 默认处理 - 也尝试提取信息
    extracted = _extract_info_by_llm(ctx, user_message, check_complaint=False)
    extracted_phone = extracted.get("phone", "")
    extracted_plate = extracted.get("license_plate", "")
    extracted_problem = extracted.get("problem", "")
    
    # 更新信息
    if extracted_phone:
        phone = extracted_phone
    if extracted_plate:
        license_plate = extracted_plate
    if extracted_problem:
        if problem_summary:
            problem_summary = f"{problem_summary}，{extracted_problem}"
        else:
            problem_summary = extracted_problem
    
    # 如果有信息更新，回到 summary_collect 阶段
    if extracted_phone or extracted_plate or extracted_problem:
        phase = "summary_collect"
        reply_content = "收到～"
    else:
        reply_content = "收到～"
    
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
