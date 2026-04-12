"""
AI 用户智能体核心逻辑
用于测试充电桩客服 AI 的多轮对话能力
"""

import json
import os
from typing import Dict, List, Optional, Any
from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.runtime_ctx.context import new_context
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from scenarios import get_scenario_prompt, SCENARIOS

# 读取配置文件
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_text_content(content) -> str:
    """
    安全地提取文本内容
    处理 LLM 返回的 content 可能是 str 或 list 的情况
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        if content and isinstance(content[0], str):
            return " ".join(content)
        else:
            # 提取多模态内容中的文本
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return " ".join(text_parts)
    return str(content)


class AIUserAgent:
    """AI 用户智能体 - 模拟真实用户测试客服系统"""

    def __init__(self, model: Optional[str] = None):
        """
        初始化智能体

        Args:
            model: 指定的模型ID，如果不指定则从配置文件读取
        """
        config = load_config()
        self.model = model or config.get("model", "doubao-seed-1-8-251228")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)

        # 初始化 LLM 客户端
        ctx = new_context(method="ai_user_agent")
        self.llm_client = LLMClient(ctx=ctx)

        # 对话历史缓存 {session_id: messages}
        self.session_history: Dict[str, List] = {}

    def _format_history(self, history: List[Dict[str, str]]) -> List:
        """
        格式化对话历史为 LangChain 消息格式

        Args:
            history: 对话历史列表，格式: [{"role": "user|assistant", "content": "..."}]

        Returns:
            LangChain 消息列表
        """
        messages = []
        for item in history:
            role = item.get("role", "user")
            content = item.get("content", "")

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        return messages

    def _parse_llm_response(self, response: AIMessage) -> Dict[str, Any]:
        """
        解析 LLM 返回的响应，提取 JSON 格式的输出

        Args:
            response: LLM 返回的消息

        Returns:
            解析后的字典，包含 user_reply 和 is_end 等字段
        """
        content = get_text_content(response.content)

        # 尝试提取 JSON
        json_data = {}

        # 查找 JSON 部分（可能被代码块包裹）
        if "```json" in content:
            # 提取代码块中的 JSON
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
        elif "```" in content:
            # 提取代码块
            start = content.find("```") + 3
            end = content.find("```", start)
            json_str = content[start:end].strip()
        else:
            # 直接尝试解析
            json_str = content.strip()

        try:
            json_data = json.loads(json_str)
        except json.JSONDecodeError:
            # 解析失败，使用整个回复作为 user_reply
            json_data = {
                "user_reply": content,
                "is_end": False,
                "current_stage": "unknown"
            }

        # 确保必填字段存在
        if "user_reply" not in json_data:
            json_data["user_reply"] = content
        if "is_end" not in json_data:
            json_data["is_end"] = False
        if "current_stage" not in json_data:
            json_data["current_stage"] = "unknown"

        return json_data

    def chat(
        self,
        scenario_type: str,
        ai_assistant_reply: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        与客服 AI 进行对话

        Args:
            scenario_type: 场景类型（standard_complaint, angry_user 等）
            ai_assistant_reply: 客服 AI 的回复
            history: 对话历史
            session_id: 会话 ID，用于管理对话历史

        Returns:
            {
                "user_reply": "用户的回复内容",
                "is_end": false,  // 是否结束对话
                "current_stage": "当前阶段",
                "scenario_type": "场景类型"
            }
        """
        # 获取场景 Prompt
        system_prompt = get_scenario_prompt(scenario_type)

        # 构建消息列表
        messages = [SystemMessage(content=system_prompt)]

        # 如果有历史记录，添加历史
        if history:
            messages.extend(self._format_history(history))

        # 添加当前客服的回复（如果是多轮对话）
        if ai_assistant_reply:
            messages.append(AIMessage(content=ai_assistant_reply))
            # 添加一个空的用户消息，让 AI 生成回复
            messages.append(HumanMessage(content="请继续对话"))

        # 调用 LLM
        response = self.llm_client.invoke(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        # 解析响应
        result = self._parse_llm_response(response)
        result["scenario_type"] = scenario_type

        # 如果有 session_id，更新历史记录
        if session_id:
            if session_id not in self.session_history:
                self.session_history[session_id] = []

            # 添加客服消息
            if ai_assistant_reply:
                self.session_history[session_id].append({
                    "role": "assistant",
                    "content": ai_assistant_reply
                })

            # 添加用户回复
            self.session_history[session_id].append({
                "role": "user",
                "content": result["user_reply"]
            })

        return result

    def reset_session(self, session_id: str):
        """重置指定会话的历史记录"""
        if session_id in self.session_history:
            del self.session_history[session_id]

    def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        """获取指定会话的历史记录"""
        return self.session_history.get(session_id, [])


# 创建全局智能体实例
_agent_instance = None


def get_agent(model: Optional[str] = None) -> AIUserAgent:
    """
    获取智能体单例

    Args:
        model: 可选的模型 ID

    Returns:
        AIUserAgent 实例
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AIUserAgent(model=model)
    return _agent_instance


# 测试代码
if __name__ == "__main__":
    # 测试标准投诉场景
    agent = get_agent()

    print("=" * 50)
    print("测试场景：标准投诉用户")
    print("=" * 50)

    # 第一轮对话
    result1 = agent.chat(scenario_type="standard_complaint")
    print(f"用户：{result1['user_reply']}")
    print(f"是否结束：{result1['is_end']}\n")

    # 第二轮对话（模拟客服回复）
    ai_reply = "您好，请问您的手机号是多少？"
    result2 = agent.chat(
        scenario_type="standard_complaint",
        ai_assistant_reply=ai_reply
    )
    print(f"客服：{ai_reply}")
    print(f"用户：{result2['user_reply']}")
    print(f"是否结束：{result2['is_end']}\n")

    # 第三轮对话
    ai_reply = "好的，请问您的车牌号是多少？"
    result3 = agent.chat(
        scenario_type="standard_complaint",
        ai_assistant_reply=ai_reply
    )
    print(f"客服：{ai_reply}")
    print(f"用户：{result3['user_reply']}")
    print(f"是否结束：{result3['is_end']}")
