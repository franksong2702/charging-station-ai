"""
清除兜底状态节点 - 在兜底流程完成后清除状态

优化点：
1. 移除 fault_keywords 关键词列表
2. 使用 LLM 智能判断用户意图
3. 保留关键词匹配作为兜底机制
"""
import os
import json
import logging
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from jinja2 import Template
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import HumanMessage

from graphs.state import ClearFallbackStateInput, ClearFallbackStateOutput
from storage.database.db import get_session
from storage.database.shared.model import ConversationHistory

# 配置日志
logger = logging.getLogger(__name__)


def _recognize_intent_for_exit(ctx, user_message: str, config: RunnableConfig) -> str:
    """
    当用户退出兜底流程时，使用 LLM 重新识别用户意图
    
    Args:
        ctx: 上下文
        user_message: 用户消息
        config: 配置
        
    Returns:
        str: 意图类型（fault_handling 或 usage_guidance）
    """
    user_message = user_message.strip()
    
    # 如果消息为空或太短，返回默认意图
    if len(user_message) < 5:
        logger.info("用户消息太短，使用默认意图 usage_guidance")
        return "usage_guidance"
    
    try:
        # 使用 LLM 判断意图
        prompt = f"""请根据用户消息，判断其意图类型。

用户消息：{user_message}

【意图类型】
1. fault_handling（故障处理）：用户遇到了充电桩故障或问题
   - 例如："充电桩充不进去电"、"充电器坏了"、"充电失败了"
   - 关键词：充不进去、充不上、坏了、故障、失败、有问题
   
2. usage_guidance（使用指导）：用户想了解如何使用充电桩
   - 例如："充电桩怎么用"、"怎么扫码充电"、"会员怎么开通"
   - 关键词：怎么、如何、使用、开通、充值

【输出】
请返回 JSON 格式：
{{"intent": "fault_handling"或"usage_guidance", "reason": "判断理由"}}

请直接返回 JSON 格式，不要其他说明："""

        # 读取配置文件获取模型配置
        cfg_file = os.path.join(
            os.getenv("COZE_WORKSPACE_PATH", ""),
            config.get("configurable", {}).get("llm_cfg", "config/intent_recognition_llm_cfg.json")
        )
        
        with open(cfg_file, 'r', encoding='utf-8') as fd:
            _cfg = json.load(fd)
        
        llm_config = _cfg.get("config", {})
        
        # 调用 LLM
        client = LLMClient(ctx=ctx)
        response = client.invoke(
            messages=[HumanMessage(content=prompt)],
            model=llm_config.get("model", "doubao-seed-1-8-251228"),
            temperature=0.1,
            max_completion_tokens=50
        )
        
        # 提取回复内容
        content = response.content
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            result_text = "".join(text_parts).strip()
        else:
            result_text = str(content).strip()
        
        # 清理可能的 markdown 代码块
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = result_text.lstrip("```json").lstrip("```").rstrip("```").strip()
        
        # 解析 JSON
        result = json.loads(result_text)
        intent = result.get("intent", "usage_guidance")
        reason = result.get("reason", "")
        
        # 验证返回值
        if intent not in ["fault_handling", "usage_guidance"]:
            logger.warning(f"LLM 返回未知意图 {intent}，使用默认意图 usage_guidance")
            intent = "usage_guidance"
        
        logger.info(f"LLM 意图识别结果: {intent}, 理由: {reason}")
        return intent
        
    except Exception as e:
        logger.error(f"LLM 意图识别失败: {str(e)}")
        # 失败时使用关键词匹配作为兜底
        logger.info("使用关键词匹配作为兜底机制")
        fault_keywords = [
            "充不进去", "充不上", "充不进", "充不了", "充电失败",
            "拔不出来", "停不下来", "充电慢", "坏了", "故障",
            "有问题", "不行", "不能用", "不能用"
        ]
        for keyword in fault_keywords:
            if keyword in user_message:
                logger.info(f"关键词匹配成功: {keyword}")
                return "fault_handling"
        
        logger.info("关键词匹配未命中，使用默认意图 usage_guidance")
        return "usage_guidance"


def clear_fallback_state_node(
    state: ClearFallbackStateInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> ClearFallbackStateOutput:
    """
    title: 清除兜底状态
    desc: 兜底流程完成后或用户退出兜底时，清除用户的兜底状态
    integrations: PostgreSQL
    """
    ctx = runtime.context

    # 识别用户的真实意图（用于后续处理）
    new_intent = _recognize_intent_for_exit(ctx, state.user_message or "", config)

    # 保存传入的 case_confirmed 值（用于路由判断）
    was_case_confirmed = state.case_confirmed

    if not state.user_id:
        logger.info("无用户 ID，跳过清除状态")
        return ClearFallbackStateOutput(
            cleared=True,
            fallback_phase="",
            phone="",
            license_plate="",
            problem_summary="",
            case_confirmed=was_case_confirmed,  # 保留原值，用于路由判断
            intent=new_intent
        )

    session = None
    try:
        session = get_session()

        # 保存一条空状态，覆盖之前的兜底状态
        # 如果 user_message 和 reply_content 为空，说明是兜底完成后的自动清除
        record = ConversationHistory(
            user_id=state.user_id,
            user_message=state.user_message or "",
            reply_content=state.reply_content or "",
            intent="" if not state.user_message else "",
            fallback_phase="",  # 清空兜底状态
            phone="",
            license_plate="",
            problem_summary="",
            entry_problem="",
            user_supplement=""
        )

        session.add(record)
        session.commit()

        logger.info(f"已清除用户 {state.user_id} 的兜底状态，新意图：{new_intent}")
        return ClearFallbackStateOutput(
            cleared=True,
            fallback_phase="",
            phone="",
            license_plate="",
            problem_summary="",
            case_confirmed=was_case_confirmed,  # 保留原值，用于路由判断
            intent=new_intent
        )

    except Exception as e:
        if session:
            session.rollback()
        logger.error(f"清除兜底状态失败：{str(e)}")
        return ClearFallbackStateOutput(
            cleared=False,
            fallback_phase="",
            phone="",
            license_plate="",
            problem_summary="",
            case_confirmed=was_case_confirmed,  # 保留原值，用于路由判断
            intent=new_intent
        )
    finally:
        if session:
            session.close()
