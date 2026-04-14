#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI User Agent x charging-station-ai 集成测试脚本。

目标：
1. 使用 AI User Agent（Coze /stream_run）模拟用户；
2. 调用 charging-station-ai（Coze /run）进行多轮对话；
3. 输出对话与结果，便于回归。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests


DEFAULT_WORKFLOW_API = "https://wp5bsz5qfm.coze.site/run"
DEFAULT_AI_USER_API = "https://jr9h465hzr.coze.site/stream_run"
DEFAULT_AI_USER_PROJECT_ID = "7627835614766841865"
PROD_WORKFLOW_API = "https://wxvghzzb8f.coze.site/run"
TEST_WORKFLOW_PROJECT_ID = "7619179949030801458"


@dataclass
class Scenario:
    name: str
    scenario_type: str
    initial_prompt: str


SCENARIOS = [
    Scenario(
        name="标准投诉流程",
        scenario_type="standard_complaint",
        initial_prompt="你是一个配合型用户，遇到充电异常扣费，请先发起投诉。",
    ),
    Scenario(
        name="情绪激动用户",
        scenario_type="angry_user",
        initial_prompt="你是一个情绪激动的用户，对充电桩服务非常不满，请先发起投诉。",
    ),
    Scenario(
        name="纠正型用户",
        scenario_type="corrective",
        initial_prompt="你是一个纠正型用户，遇到客服复述错误会纠正，请先发起投诉。",
    ),
]


def require_env(name: str, default: str = "") -> str:
    value = os.getenv(name, default).strip()
    if not value:
        raise ValueError(f"缺少环境变量: {name}")
    return value


def strip_think_tags(text: str) -> str:
    text = re.sub(
        r"<\[SILENT_never_used_[a-f0-9]+\]></think_never_used_[a-f0-9]+>",
        "",
        text,
    )
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


def call_ai_user_agent(
    *,
    api_url: str,
    token: str,
    project_id: str,
    query: str,
    scenario_type: str,
    session_id: str = "",
    timeout: int = 90,
) -> dict[str, str] | None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {
        "content": {
            "query": {
                "prompt": [
                    {
                        "type": "text",
                        "content": {
                            "text": (
                                f"[SCENARIO={scenario_type}] {query}"
                                if scenario_type
                                else query
                            )
                        },
                    }
                ]
            }
        },
        "type": "query",
        "session_id": session_id,
        "project_id": project_id,
    }

    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=timeout,
        )
        if response.status_code != 200:
            print(f"[AI 用户] HTTP {response.status_code}: {response.text[:200]}")
            return None

        answer_parts: list[str] = []
        next_session_id = session_id
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if event.get("type") == "answer":
                content = event.get("content") or {}
                piece = content.get("answer", "")
                if piece:
                    answer_parts.append(piece)
            if event.get("session_id"):
                next_session_id = event["session_id"]

        return {
            "reply": strip_think_tags("".join(answer_parts)),
            "session_id": next_session_id,
        }
    except Exception as exc:
        print(f"[AI 用户] 调用失败: {exc}")
        return None


def call_ai_service(
    *,
    api_url: str,
    token: str,
    user_message: str,
    user_id: str,
    conversation_history: list[dict[str, str]],
    timeout: int = 90,
) -> str | None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "user_message": user_message,
        "user_id": user_id,
        "conversation_history": conversation_history,
    }

    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        if response.status_code != 200:
            print(f"[AI 客服] HTTP {response.status_code}: {response.text[:200]}")
            return None
        data = response.json()
        return data.get("reply_content", "")
    except Exception as exc:
        print(f"[AI 客服] 调用失败: {exc}")
        return None


def run_scenario(
    *,
    scenario: Scenario,
    ai_user_api: str,
    ai_user_token: str,
    ai_user_project_id: str,
    workflow_api: str,
    workflow_token: str,
    max_turns: int,
) -> dict[str, Any]:
    print(f"\n{'=' * 72}")
    print(f"场景: {scenario.name} ({scenario.scenario_type})")
    print("=" * 72)

    workflow_user_id = f"ai_user_it_{scenario.scenario_type}_{int(time.time())}"
    ai_user_session_id = ""
    conversation: list[dict[str, str]] = []
    turn = 0
    exit_reason = "达到最大轮数"

    user_result = call_ai_user_agent(
        api_url=ai_user_api,
        token=ai_user_token,
        project_id=ai_user_project_id,
        query=scenario.initial_prompt,
        scenario_type=scenario.scenario_type,
        session_id=ai_user_session_id,
    )
    if not user_result or not user_result.get("reply"):
        return {"success": False, "scenario": scenario.name, "error": "AI 用户首轮失败"}

    user_message = user_result["reply"]
    ai_user_session_id = user_result.get("session_id", "")
    conversation.append({"role": "user", "content": user_message})
    turn += 1
    print(f"[{turn}] 👤 用户: {user_message}")

    while turn < max_turns:
        service_reply = call_ai_service(
            api_url=workflow_api,
            token=workflow_token,
            user_message=user_message,
            user_id=workflow_user_id,
            conversation_history=conversation,
        )
        if not service_reply:
            return {"success": False, "scenario": scenario.name, "error": "AI 客服调用失败"}

        conversation.append({"role": "assistant", "content": service_reply})
        print(f"[{turn}] 🤖 客服: {service_reply}")

        if "工单" in service_reply and "创建" in service_reply:
            exit_reason = "工单创建成功"
            break
        if "祝您生活愉快" in service_reply:
            exit_reason = "对话结束"
            break

        followup_prompt = (
            f"客服说：{service_reply}\n"
            "请继续按你的场景身份回复。"
            "若客服明确问手机号/车牌号再回答；若在确认环节请明确确认或拒绝。"
        )
        user_result = call_ai_user_agent(
            api_url=ai_user_api,
            token=ai_user_token,
            project_id=ai_user_project_id,
            query=followup_prompt,
            scenario_type=scenario.scenario_type,
            session_id=ai_user_session_id,
        )
        if not user_result or not user_result.get("reply"):
            return {"success": False, "scenario": scenario.name, "error": "AI 用户续轮失败"}

        user_message = user_result["reply"]
        ai_user_session_id = user_result.get("session_id", ai_user_session_id)
        conversation.append({"role": "user", "content": user_message})
        turn += 1
        print(f"[{turn}] 👤 用户: {user_message}")
        time.sleep(0.5)

    return {
        "success": True,
        "scenario": scenario.name,
        "scenario_type": scenario.scenario_type,
        "total_turns": turn,
        "exit_reason": exit_reason,
        "workflow_user_id": workflow_user_id,
        "conversation": conversation,
    }


def save_report(results: list[dict[str, Any]]) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"/tmp/ai_user_integration_test_{ts}.md"
    lines = [
        "# AI User Agent x charging-station-ai 集成测试报告",
        "",
        f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 总场景: {len(results)}",
        f"- 成功: {sum(1 for x in results if x.get('success'))}",
        "",
    ]
    for idx, item in enumerate(results, start=1):
        ok = "✅" if item.get("success") else "❌"
        lines.append(f"## {ok} 场景{idx}: {item.get('scenario', '未知')}")
        if not item.get("success"):
            lines.append(f"- 错误: {item.get('error', '未知错误')}")
            lines.append("")
            continue
        lines.append(f"- 类型: {item.get('scenario_type')}")
        lines.append(f"- 轮数: {item.get('total_turns')}")
        lines.append(f"- 结束原因: {item.get('exit_reason')}")
        lines.append(f"- 客服 user_id: {item.get('workflow_user_id')}")
        lines.append("")
        for msg in item.get("conversation", []):
            role = "👤 用户" if msg["role"] == "user" else "🤖 客服"
            lines.append(f"- {role}: {msg['content']}")
        lines.append("")

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI User Agent 集成测试")
    parser.add_argument("--max-turns", type=int, default=8, help="每个场景最大轮数")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        workflow_token = require_env("COZE_API_TOKEN")
        ai_user_token = require_env("AI_USER_AGENT_TOKEN")
        workflow_api = os.getenv("COZE_WORKFLOW_API", DEFAULT_WORKFLOW_API).strip()
        ai_user_api = os.getenv("AI_USER_AGENT_API", DEFAULT_AI_USER_API).strip()
        ai_user_project_id = os.getenv(
            "AI_USER_AGENT_PROJECT_ID", DEFAULT_AI_USER_PROJECT_ID
        ).strip()
        target_project_id = os.getenv(
            "COZE_WORKFLOW_PROJECT_ID", TEST_WORKFLOW_PROJECT_ID
        ).strip()
    except ValueError as exc:
        print(f"配置错误: {exc}")
        return 2

    # Safety guard: by default this script is ONLY for test project formal env.
    allow_prod = os.getenv("ALLOW_PROD_TEST", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if not allow_prod:
        if workflow_api == PROD_WORKFLOW_API:
            print("安全拦截: 检测到线上项目正式环境 URL，已拒绝执行测试。")
            print("如确需覆盖，请显式设置 ALLOW_PROD_TEST=true。")
            return 3
        if target_project_id != TEST_WORKFLOW_PROJECT_ID:
            print(
                "安全拦截: COZE_WORKFLOW_PROJECT_ID 不是测试项目 "
                f"({TEST_WORKFLOW_PROJECT_ID})，已拒绝执行。"
            )
            print("如确需覆盖，请显式设置 ALLOW_PROD_TEST=true。")
            return 3

    results: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        result = run_scenario(
            scenario=scenario,
            ai_user_api=ai_user_api,
            ai_user_token=ai_user_token,
            ai_user_project_id=ai_user_project_id,
            workflow_api=workflow_api,
            workflow_token=workflow_token,
            max_turns=args.max_turns,
        )
        results.append(result)
        time.sleep(1)

    report_path = save_report(results)
    passed = sum(1 for x in results if x.get("success"))
    print(f"\n完成: {passed}/{len(results)} 场景成功")
    print(f"报告: {report_path}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
