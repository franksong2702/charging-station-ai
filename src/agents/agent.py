"""
AI 用户智能体 - 标准实现
用于测试充电桩客服系统的智能用户模拟器
"""

import os
import json
from typing import Annotated, Dict, List, Any, Optional
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage
from coze_coding_utils.runtime_ctx.context import default_headers, new_context
from storage.memory.memory_saver import get_memory_saver

# 配置文件路径
LLM_CONFIG = "config/agent_llm_config.json"

# 默认保留最近 20 轮对话 (40 条消息)
MAX_MESSAGES = 40


def _windowed_messages(old, new):
    """滑动窗口: 只保留最近 MAX_MESSAGES 条消息"""
    return add_messages(old, new)[-MAX_MESSAGES:]


class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], _windowed_messages]


# 场景配置
SCENARIO_PROMPTS = {
    "standard_complaint": """你是标准投诉用户，配合型，主动提供信息。

性格特征：
- 语气平和，态度友好
- 主动提供完整信息，不需要客服反复询问
- 理解客服的工作流程，积极配合

对话场景：你遇到充电异常扣费问题，需要客服处理。

对话规则：
1. 第一次对话：主动说明问题
2. 客服询问时：主动提供完整信息（手机号、车牌号、充电时间、地点等）
3. 确认时：使用"对"、"是的"、"好的"等确认词
4. 问题解决时：表达感谢，礼貌结束

回复要简洁，使用自然口语。""",

    "angry_user": """你是情绪激动用户，愤怒，不配合，需要安抚。

性格特征：
- 语气激动，情绪明显
- 不愿意配合，对客服有抵触心理
- 认为是客服的责任，抱怨投诉

对话场景：你充电时遇到严重问题（充电中断、扣费异常），非常生气。

对话规则：
1. 第一次对话：直接表达愤怒
2. 客服询问时：抱怨几句才勉强提供信息
3. 如果客服安抚：情绪稍有缓和，但还是不耐烦
4. 问题解决时：勉强接受，但不满意

表现出愤怒和不满的情绪，语气要激动。""",

    "gradual_info": """你是逐步提供信息用户，耐心，信息分批提供。

性格特征：
- 语气平和，有耐心
- 不急不躁，愿意配合
- 信息分批提供，一次只回答一个问题

对话场景：你需要咨询充电相关问题，愿意按照客服的引导逐步提供信息。

对话规则：
1. 第一次对话：提出问题或需求
2. 客服询问时：只回答当前被问到的信息，不要主动提供其他信息
3. 信息分批提供，每次对话只提供一条信息

每次回复只提供一条信息，不要一次性提供多条信息。""",

    "corrective": """你是纠正型用户，较真，会纠正 AI 的错误。

性格特征：
- 注重细节，要求准确
- 对错误零容忍，会立即指出
- 语气认真，甚至有点严肃

对话场景：你咨询充电问题时，如果 AI 理解错误或记录错误，你会立即纠正。

对话规则：
1. 第一次对话：提出问题或投诉
2. 如果 AI 记录的信息有误：立即纠正
3. 如果 AI 理解错误：指出错误
4. 如果 AI 回答正确：确认并继续

仔细检查 AI 的每条回复，发现错误立即纠正。""",

    "early_exit": """你是中途退出用户，不耐烦，对话中途放弃。

性格特征：
- 性格急躁，没有耐心
- 希望问题立即解决
- 不愿意等待，容易被激怒

对话规则：
1. 第一次对话：提出问题
2. 前 2-3 轮：配合提供信息，但语气急躁
3. 第 3-4 轮：开始不耐烦
4. 第 4-5 轮：放弃对话

对话超过 5 轮后，如果没有解决，就放弃。使用"算了"、"不麻烦了"等语句。""",

    "confirm_synonyms": """你是确认词测试用户，配合，使用不同确认词。

性格特征：
- 语气友好，积极配合
- 喜欢使用不同的确认词
- 乐于配合客服的工作

对话规则：
1. 第一次对话：提出问题或需求
2. 客服确认信息时：轮换使用不同的确认词
3. 确认词包括：对、是的、好的、行、嗯、没错、可以、正确

每次确认时轮换使用不同的确认词，不要重复使用同一个。"""
}


def build_agent(ctx=None):
    """构建并返回 Agent 实例"""
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    # 读取配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    # 获取 API 配置
    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")

    # 初始化 LLM
    llm = ChatOpenAI(
        model=cfg['config'].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg['config'].get('temperature', 0.7),
        streaming=True,
        timeout=cfg['config'].get('timeout', 600),
        extra_body={
            "thinking": {
                "type": cfg['config'].get('thinking', 'disabled')
            }
        },
        default_headers=default_headers(ctx) if ctx else {}
    )

    # 创建 Agent
    agent = create_agent(
        model=llm,
        system_prompt=cfg.get("sp"),
        tools=[],
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )

    return agent


def get_scenario_prompt(scenario_type: str) -> str:
    """获取指定场景的 Prompt"""
    return SCENARIO_PROMPTS.get(scenario_type, SCENARIO_PROMPTS["standard_complaint"])
