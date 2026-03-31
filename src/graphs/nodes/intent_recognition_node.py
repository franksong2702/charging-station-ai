"""
意图识别节点 - 判断用户问题的类型
支持：使用指导、故障处理、投诉兜底、轻度不满、满意、评价反馈
"""
import os
import re
import json
from typing import Dict, Any
from jinja2 import Template

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import SystemMessage, HumanMessage

from graphs.state import IntentRecognitionInput, IntentRecognitionOutput


def intent_recognition_node(
    state: IntentRecognitionInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> IntentRecognitionOutput:
    """
    title: 意图识别
    desc: 分析用户消息，判断问题类型。强烈不满/转人工走兜底，轻度不满继续尝试帮助
    integrations: 大语言模型
    """
    # 获取上下文
    ctx = runtime.context
    
    user_message = state.user_message.strip()
    
    # ==================== 检查是否在兜底流程中 ====================
    # 如果 fallback_phase 不为空，需要判断用户是想继续兜底还是问新问题
    if state.fallback_phase:
        # 1. 检查是否是取消兜底
        cancel_keywords = ["取消", "不用了", "算了", "不需要了", "不用管了", "没事了", "不要了", "不麻烦了"]
        for keyword in cancel_keywords:
            if keyword in user_message:
                # 用户取消兜底，清空状态，正常识别意图
                return IntentRecognitionOutput(intent="cancel_fallback")
        
        # 2. 检查是否是兜底流程相关输入（手机号、车牌号、确认等）
        # 手机号模式：11位数字或带分隔符的格式
        phone_pattern = r'1[3-9]\d[\s\-]?\d{4}[\s\-]?\d{4}|1[3-9]\d{9}|手机|电话'
        # 车牌号模式：省份简称+字母+数字/字母
        plate_pattern = r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{4,6}|车牌'
        # 确认关键词
        confirm_keywords = ["确认", "确认无误", "没问题", "是的", "对", "好的"]
        # 补充说明关键词
        supplement_keywords = ["补充", "还有", "另外", "对了", "还有个问题"]
        
        is_phone_input = bool(re.search(phone_pattern, user_message, re.IGNORECASE))
        is_plate_input = bool(re.search(plate_pattern, user_message, re.IGNORECASE))
        is_confirm = user_message in confirm_keywords
        is_supplement = any(kw in user_message for kw in supplement_keywords)
        
        # 如果是兜底相关输入，继续兜底流程
        if is_phone_input or is_plate_input or is_confirm or is_supplement:
            return IntentRecognitionOutput(intent="fallback")
        
        # 3. 检查是否是明显的新问题（包含问题特征）
        question_patterns = [
            r'怎么', r'如何', r'为什么', r'什么', r'哪', r'？', r'\?',
            r'帮我', r'请问', r'咨询', r'想问', r'想了解',
            r'充电', r'特斯拉', r'新能源', r'扫码', r'操作'
        ]
        
        is_new_question = any(re.search(p, user_message) for p in question_patterns)
        
        if is_new_question:
            # 用户在问新问题，退出兜底流程
            return IntentRecognitionOutput(intent="exit_fallback")
        
        # 4. 其他情况继续兜底流程
        return IntentRecognitionOutput(intent="fallback")
    
    # ==================== 优先判断特殊意图 ====================
    
    # 1. 评价反馈（支持半角/全角）
    if user_message in ["1", "１", "【1】", "【１】"]:
        return IntentRecognitionOutput(intent="feedback_good")
    if user_message in ["2", "２", "【2】", "【２】"]:
        return IntentRecognitionOutput(intent="feedback_bad")
    # 文字形式评价
    if user_message in ["很好", "满意", "有帮助"]:
        return IntentRecognitionOutput(intent="feedback_good")
    if user_message in ["没有帮助", "不满意", "没用"]:
        return IntentRecognitionOutput(intent="feedback_bad")
    
    # 2. 故障处理（优先判断，避免被误判为兜底）
    # 充电相关问题关键词
    fault_keywords = ["充不进去", "充不上", "充不进", "充不了", "充不起", 
                      "充电失败", "充不进电", "充不上电",
                      "拔不出来", "停不下来", "充电慢", "坏了", "故障"]
    for keyword in fault_keywords:
        if keyword in user_message:
            return IntentRecognitionOutput(intent="fault_handling")
    
    # 3. 强烈不满或转人工 → 走兜底流程
    # 强烈不满关键词（情绪激烈，需要人工介入）
    strong_dissatisfied_keywords = ["太差了", "垃圾", "投诉你", "什么破", "什么垃圾", 
                                    "要投诉", "强烈不满", "气死我了", "骗子", "坑人",
                                    "转人工", "人工客服", "转接人工", "接人工", "人工服务", "转客服"]
    for keyword in strong_dissatisfied_keywords:
        if keyword in user_message:
            return IntentRecognitionOutput(intent="fallback")
    
    # 4. 轻度不满 → AI 继续尝试帮助
    # 轻度不满关键词（可以尝试继续帮助）
    mild_dissatisfied_keywords = ["没用", "不行", "还是不行", "没帮助", "不好用", 
                                  "没解决", "帮不了", "还是不会", "搞不定",
                                  "为什么没有", "什么时候", "怎么没有", "为什么找不到"]
    for keyword in mild_dissatisfied_keywords:
        if keyword in user_message:
            return IntentRecognitionOutput(intent="dissatisfied")
    
    # 5. 满意（用户表达感谢）
    satisfied_keywords = ["谢谢", "感谢", "好的好的", "好的 谢谢", "谢谢你", "多谢", "谢谢啦"]
    for keyword in satisfied_keywords:
        if keyword in user_message:
            return IntentRecognitionOutput(intent="satisfied")
    
    # ==================== 调用 LLM 判断复杂意图 ====================
    
    # 读取配置文件
    cfg_file = os.path.join(
        os.getenv("COZE_WORKSPACE_PATH", ""),
        config.get("configurable", {}).get("llm_cfg", "config/intent_recognition_llm_cfg.json")
    )
    
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)
    
    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")
    
    # 使用 Jinja2 渲染用户提示词
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({"user_message": state.user_message})
    
    # 初始化 LLM 客户端
    client = LLMClient(ctx=ctx)
    
    # 构建消息
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]
    
    # 调用 LLM
    response = client.invoke(
        messages=messages,
        model=llm_config.get("model", "doubao-seed-1-8-251228"),
        temperature=llm_config.get("temperature", 0.3),
        max_completion_tokens=llm_config.get("max_completion_tokens", 500)
    )
    
    # 解析意图
    content = response.content
    if isinstance(content, list):
        # 处理多模态返回
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif isinstance(item, str):
                text_parts.append(item)
        intent_text = " ".join(text_parts).strip()
    else:
        intent_text = str(content).strip()
    
    # 提取意图关键词
    intent = "usage_guidance"  # 默认值
    if "使用指导" in intent_text:
        intent = "usage_guidance"
    elif "故障处理" in intent_text:
        intent = "fault_handling"
    elif "投诉" in intent_text:
        intent = "complaint"
    elif "兜底" in intent_text or "强烈不满" in intent_text:
        intent = "fallback"
    elif "不满意" in intent_text:
        intent = "dissatisfied"
    elif "满意" in intent_text:
        intent = "satisfied"
    
    return IntentRecognitionOutput(intent=intent)
