"""
AI 用户智能体 REST API
提供 HTTP 接口供外部调用
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from agent import get_agent, AIUserAgent
from scenarios import list_scenarios, get_scenario_info, SCENARIOS

# 创建 FastAPI 应用
app = FastAPI(
    title="AI 用户智能体 API",
    description="用于测试充电桩客服 AI 的智能用户模拟器",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 数据模型 =====

class ChatRequest(BaseModel):
    """对话请求"""
    scenario_type: str = Field(
        ...,
        description="场景类型",
        example="standard_complaint"
    )
    ai_assistant_reply: Optional[str] = Field(
        None,
        description="客服 AI 的回复（多轮对话时需要）",
        example="您好，请问您的手机号是多少？"
    )
    history: Optional[List[Dict[str, str]]] = Field(
        None,
        description="对话历史",
        example=[
            {"role": "user", "content": "你好，我遇到充电异常扣费问题了"},
            {"role": "assistant", "content": "您好，请问您的手机号是多少？"}
        ]
    )
    session_id: Optional[str] = Field(
        None,
        description="会话 ID，用于管理对话历史",
        example="session_123456"
    )


class ChatResponse(BaseModel):
    """对话响应"""
    user_reply: str = Field(..., description="用户的回复内容")
    is_end: bool = Field(..., description="是否结束对话")
    current_stage: str = Field(..., description="当前对话阶段")
    scenario_type: str = Field(..., description="场景类型")
    # 附加字段（根据场景可能不同）
    extra: Optional[Dict[str, Any]] = Field(None, description="额外信息")


class ScenarioInfo(BaseModel):
    """场景信息"""
    type: str = Field(..., description="场景类型")
    name: str = Field(..., description="场景名称")
    description: str = Field(..., description="场景描述")


class SessionResetRequest(BaseModel):
    """会话重置请求"""
    session_id: str = Field(..., description="会话 ID")


# ===== 全局变量 =====
_agent: Optional[AIUserAgent] = None


def get_current_agent() -> AIUserAgent:
    """获取当前智能体实例"""
    global _agent
    if _agent is None:
        _agent = get_agent()
    return _agent


# ===== API 路由 =====

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "AI 用户智能体 API",
        "version": "1.0.0",
        "endpoints": {
            "/scenarios": "获取所有可用场景",
            "/chat": "对话接口",
            "/scenario/{type}": "获取指定场景信息",
            "/session/reset": "重置会话历史"
        }
    }


@app.get("/scenarios", response_model=List[ScenarioInfo])
async def get_scenarios():
    """
    获取所有可用的测试场景

    Returns:
        场景列表
    """
    return list_scenarios()


@app.get("/scenario/{scenario_type}", response_model=Dict[str, Any])
async def get_scenario_detail(scenario_type: str):
    """
    获取指定场景的详细信息

    Args:
        scenario_type: 场景类型

    Returns:
        场景详细信息
    """
    try:
        info = get_scenario_info(scenario_type)
        return {
            "type": scenario_type,
            **info
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    与 AI 用户智能体对话

    Args:
        request: 对话请求

    Returns:
        用户回复及对话状态

    Example:
        # 第一次对话
        POST /chat
        {
            "scenario_type": "standard_complaint",
            "session_id": "session_001"
        }

        # 多轮对话
        POST /chat
        {
            "scenario_type": "standard_complaint",
            "ai_assistant_reply": "您好，请问您的手机号是多少？",
            "session_id": "session_001"
        }
    """
    # 验证场景类型
    if request.scenario_type not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario type. Available: {list(SCENARIOS.keys())}"
        )

    try:
        agent = get_current_agent()

        result = agent.chat(
            scenario_type=request.scenario_type,
            ai_assistant_reply=request.ai_assistant_reply,
            history=request.history,
            session_id=request.session_id
        )

        # 提取额外字段
        extra_fields = {}
        for key in result.keys():
            if key not in ["user_reply", "is_end", "current_stage", "scenario_type"]:
                extra_fields[key] = result[key]

        return ChatResponse(
            user_reply=result["user_reply"],
            is_end=result["is_end"],
            current_stage=result["current_stage"],
            scenario_type=result["scenario_type"],
            extra=extra_fields if extra_fields else None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/reset")
async def reset_session(request: SessionResetRequest):
    """
    重置指定会话的历史记录

    Args:
        request: 会话重置请求

    Returns:
        重置结果
    """
    try:
        agent = get_current_agent()
        agent.reset_session(request.session_id)
        return {
            "message": f"Session {request.session_id} has been reset",
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """
    获取指定会话的历史记录

    Args:
        session_id: 会话 ID

    Returns:
        对话历史
    """
    try:
        agent = get_current_agent()
        history = agent.get_session_history(session_id)
        return {
            "session_id": session_id,
            "history": history,
            "turn_count": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "agent_initialized": _agent is not None
    }


# ===== 启动服务 =====

def start_server(host: str = "0.0.0.0", port: int = 8000):
    """
    启动 API 服务器

    Args:
        host: 监听地址
        port: 监听端口
    """
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    print("Starting AI User Agent API Server...")
    start_server()
