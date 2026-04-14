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
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests


DEFAULT_WORKFLOW_API = "https://wp5bsz5qfm.coze.site/run"
DEFAULT_AI_USER_API = "https://jr9h465hzr.coze.site/stream_run"
DEFAULT_AI_USER_PROJECT_ID = "7627835614766841865"
PROD_WORKFLOW_API = "https://wxvghzzb8f.coze.site/run"
TEST_WORKFLOW_PROJECT_ID = "7619179949030801458"
DEFAULT_MAILBOX = "INBOX"
DEFAULT_IMAP_HOST = "imap.qq.com"
DEFAULT_IMAP_PORT = 993
DEFAULT_EMAIL_POLL_SECONDS = 120


@dataclass
class Scenario:
    name: str
    scenario_type: str
    initial_prompt: str
    expect_case_created: bool = True


@dataclass
class UserProfile:
    profile_id: str
    scenario_type: str
    base_user_id: str
    phone: str
    license_plate: str
    complaint_opening: str
    confirmation_reply: str = "确认"


@dataclass
class MailConfig:
    enabled: bool
    host: str
    port: int
    username: str
    password: str
    mailbox: str
    sender_filter: str
    subject_keyword: str
    poll_seconds: int
    max_scan: int
    lookback_minutes: int


@dataclass
class MailCheckResult:
    checked: bool
    found: bool
    status: str
    reason: str
    matched_by: str
    subject: str
    sent_at: str
    from_addr: str
    to_addr: str
    body_preview: str
    checks: dict[str, bool]
    missing: list[str]


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


def read_latest_coze_cli_token() -> str:
    config_path = os.path.expanduser("~/.coze/config.json")
    if not os.path.exists(config_path):
        return ""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return (data.get("accessToken") or "").strip()
    except Exception:
        return ""


def strip_think_tags(text: str) -> str:
    text = re.sub(
        r"<\[SILENT_never_used_[a-f0-9]+\]></think_never_used_[a-f0-9]+>",
        "",
        text,
    )
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


def normalize_phone(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def normalize_license_plate(text: str) -> str:
    return (text or "").replace(" ", "").upper()


def is_valid_phone(text: str) -> bool:
    return bool(re.fullmatch(r"1[3-9]\d{9}", normalize_phone(text)))


def is_valid_plate(text: str) -> bool:
    plate = normalize_license_plate(text)
    return bool(re.fullmatch(r"[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}", plate))


def sanitize_message(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def escape_sql_literal(text: str) -> str:
    return (text or "").replace("'", "''")


def decode_mime_header(raw: str | None) -> str:
    if not raw:
        return ""
    pieces: list[str] = []
    for part, enc in decode_header(raw):
        if isinstance(part, bytes):
            pieces.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            pieces.append(part)
    return "".join(pieces).strip()


def html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_email_bodies(message: email.message.Message) -> tuple[str, str]:
    text_parts: list[str] = []
    html_parts: list[str] = []
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            content_type = (part.get_content_type() or "").lower()
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                decoded = payload.decode(charset, errors="replace")
            except LookupError:
                decoded = payload.decode("utf-8", errors="replace")
            if content_type == "text/plain":
                text_parts.append(decoded)
            elif content_type == "text/html":
                html_parts.append(decoded)
    else:
        payload = message.get_payload(decode=True)
        if payload:
            charset = message.get_content_charset() or "utf-8"
            try:
                decoded = payload.decode(charset, errors="replace")
            except LookupError:
                decoded = payload.decode("utf-8", errors="replace")
            if message.get_content_type().lower() == "text/html":
                html_parts.append(decoded)
            else:
                text_parts.append(decoded)
    return "\n".join(text_parts).strip(), "\n".join(html_parts).strip()


def guess_phone_from_conversation(conversation: list[dict[str, str]]) -> str:
    phone_re = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
    for msg in conversation:
        if msg.get("role") != "user":
            continue
        match = phone_re.search(msg.get("content", ""))
        if match:
            return match.group(1)
    return ""


def load_user_profiles(profile_path: str) -> dict[str, UserProfile]:
    with open(profile_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    profiles: dict[str, UserProfile] = {}
    for item in raw.get("profiles", []):
        profile = UserProfile(
            profile_id=item["profile_id"],
            scenario_type=item["scenario_type"],
            base_user_id=item["base_user_id"],
            phone=item["phone"],
            license_plate=item["license_plate"],
            complaint_opening=item["complaint_opening"],
            confirmation_reply=item.get("confirmation_reply", "确认"),
        )
        if not is_valid_phone(profile.phone):
            raise ValueError(
                f"profile {profile.profile_id} phone 非法: {profile.phone}"
            )
        if not is_valid_plate(profile.license_plate):
            raise ValueError(
                f"profile {profile.profile_id} 车牌非法: {profile.license_plate}"
            )
        profiles[profile.scenario_type] = profile
    return profiles


def build_mail_check_result(
    *,
    checked: bool,
    found: bool,
    status: str,
    reason: str,
    matched_by: str = "",
    subject: str = "",
    sent_at: str = "",
    from_addr: str = "",
    to_addr: str = "",
    body_preview: str = "",
    checks: dict[str, bool] | None = None,
    missing: list[str] | None = None,
) -> dict[str, Any]:
    result = MailCheckResult(
        checked=checked,
        found=found,
        status=status,
        reason=reason,
        matched_by=matched_by,
        subject=subject,
        sent_at=sent_at,
        from_addr=from_addr,
        to_addr=to_addr,
        body_preview=body_preview,
        checks=checks or {},
        missing=missing or [],
    )
    return {
        "checked": result.checked,
        "found": result.found,
        "status": result.status,
        "reason": result.reason,
        "matched_by": result.matched_by,
        "subject": result.subject,
        "sent_at": result.sent_at,
        "from_addr": result.from_addr,
        "to_addr": result.to_addr,
        "body_preview": result.body_preview,
        "checks": result.checks,
        "missing": result.missing,
    }


def load_mail_config() -> MailConfig:
    enabled = os.getenv("ENABLE_EMAIL_CHECK", "true").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    return MailConfig(
        enabled=enabled,
        host=os.getenv("TEST_EMAIL_IMAP_HOST", DEFAULT_IMAP_HOST).strip(),
        port=int(os.getenv("TEST_EMAIL_IMAP_PORT", str(DEFAULT_IMAP_PORT)).strip()),
        username=os.getenv("TEST_EMAIL_IMAP_USERNAME", "").strip(),
        password=os.getenv("TEST_EMAIL_IMAP_PASSWORD", "").strip(),
        mailbox=os.getenv("TEST_EMAIL_IMAP_MAILBOX", DEFAULT_MAILBOX).strip() or DEFAULT_MAILBOX,
        sender_filter=os.getenv("TEST_EMAIL_SENDER_FILTER", "").strip(),
        subject_keyword=os.getenv("TEST_EMAIL_SUBJECT_KEYWORD", "【充电桩客服】用户问题反馈").strip(),
        poll_seconds=int(
            os.getenv("TEST_EMAIL_POLL_SECONDS", str(DEFAULT_EMAIL_POLL_SECONDS)).strip()
        ),
        max_scan=int(os.getenv("TEST_EMAIL_MAX_SCAN", "80").strip()),
        lookback_minutes=int(os.getenv("TEST_EMAIL_LOOKBACK_MINUTES", "60").strip()),
    )


def find_and_validate_fallback_email(
    *,
    mail_cfg: MailConfig,
    workflow_user_id: str,
    scenario_start_ts: float,
    conversation: list[dict[str, str]],
) -> dict[str, Any]:
    if not mail_cfg.enabled:
        return build_mail_check_result(
            checked=False,
            found=False,
            status="SKIPPED",
            reason="邮箱校验已禁用（ENABLE_EMAIL_CHECK=false）",
        )
    if not mail_cfg.username or not mail_cfg.password:
        return build_mail_check_result(
            checked=False,
            found=False,
            status="SKIPPED",
            reason="缺少 TEST_EMAIL_IMAP_USERNAME / TEST_EMAIL_IMAP_PASSWORD，无法校验邮件",
        )

    start_window = scenario_start_ts - min(max(mail_cfg.lookback_minutes * 60, 0), 120)
    deadline = time.time() + max(mail_cfg.poll_seconds, 1)
    phone = guess_phone_from_conversation(conversation)
    first_user_message = ""
    for msg in conversation:
        if msg.get("role") == "user" and msg.get("content"):
            first_user_message = msg["content"][:40]
            break

    last_error = ""
    while time.time() <= deadline:
        try:
            with imaplib.IMAP4_SSL(mail_cfg.host, mail_cfg.port) as mail:
                mail.login(mail_cfg.username, mail_cfg.password)
                select_status, _ = mail.select(mail_cfg.mailbox)
                if select_status != "OK":
                    return build_mail_check_result(
                        checked=True,
                        found=False,
                        status="FAILED",
                        reason=f"无法选择邮箱文件夹: {mail_cfg.mailbox}",
                    )

                search_status, search_data = mail.search(None, "ALL")
                if search_status != "OK" or not search_data or not search_data[0]:
                    time.sleep(3)
                    continue

                all_ids = search_data[0].split()
                scan_ids = all_ids[-mail_cfg.max_scan :]
                scan_ids.reverse()

                for msg_id in scan_ids:
                    fetch_status, fetched = mail.fetch(msg_id, "(RFC822)")
                    if fetch_status != "OK" or not fetched or not fetched[0]:
                        continue
                    raw_bytes = fetched[0][1]
                    if not raw_bytes:
                        continue
                    parsed = email.message_from_bytes(raw_bytes)
                    subject = decode_mime_header(parsed.get("Subject"))
                    from_addr = decode_mime_header(parsed.get("From"))
                    to_addr = decode_mime_header(parsed.get("To"))
                    date_header = parsed.get("Date")
                    sent_at = ""
                    sent_ts = None
                    if date_header:
                        try:
                            dt = parsedate_to_datetime(date_header)
                            sent_at = dt.isoformat()
                            sent_ts = dt.timestamp()
                        except Exception:
                            sent_at = date_header

                    if sent_ts and sent_ts < start_window:
                        continue
                    if mail_cfg.subject_keyword and mail_cfg.subject_keyword not in subject:
                        continue
                    if mail_cfg.sender_filter and mail_cfg.sender_filter not in from_addr:
                        continue

                    text_body, html_body = extract_email_bodies(parsed)
                    normalized_body = " ".join(
                        x for x in [text_body, html_to_text(html_body)] if x
                    )
                    matched_by = ""
                    # When workflow_user_id is available, enforce exact traceability.
                    if workflow_user_id:
                        if workflow_user_id in normalized_body:
                            matched_by = "workflow_user_id"
                        else:
                            continue
                    else:
                        if phone and phone in subject + " " + normalized_body:
                            matched_by = "phone"
                        elif first_user_message and first_user_message in normalized_body:
                            matched_by = "first_user_message"
                    if not matched_by:
                        continue

                    checks = {
                        "has_phone": bool(phone and phone in normalized_body + " " + subject),
                        "has_license_plate_label": "车牌" in normalized_body,
                        "has_problem_summary_label": "问题总结" in normalized_body,
                        "has_conversation_label": "完整对话记录" in normalized_body,
                        "has_workflow_user_id": bool(
                            workflow_user_id and workflow_user_id in normalized_body
                        ),
                    }
                    missing = [name for name, ok in checks.items() if not ok]
                    preview = normalized_body[:800]
                    if sent_at:
                        pass
                    else:
                        sent_at = datetime.now().isoformat()
                    return build_mail_check_result(
                        checked=True,
                        found=True,
                        status="PASSED" if not missing else "FAILED",
                        reason="邮件校验通过" if not missing else "邮件已命中但关键信息缺失",
                        matched_by=matched_by,
                        subject=subject,
                        sent_at=sent_at,
                        from_addr=from_addr,
                        to_addr=to_addr,
                        body_preview=preview,
                        checks=checks,
                        missing=missing,
                    )
        except Exception as exc:
            last_error = str(exc)

        time.sleep(3)

    return build_mail_check_result(
        checked=True,
        found=False,
        status="FAILED",
        reason=(
            f"在 {mail_cfg.poll_seconds}s 内未找到匹配邮件"
            if not last_error
            else f"邮箱查询失败: {last_error}"
        ),
    )


def fetch_case_records_for_user(
    *,
    workflow_api: str,
    workflow_token: str,
    workflow_user_id: str,
    timeout: int = 60,
) -> dict[str, Any]:
    if "/run" not in workflow_api:
        return {
            "checked": True,
            "status": "FAILED",
            "reason": "workflow_api 不是 /run 地址，无法推导 /db/execute",
            "found": False,
            "records": [],
        }
    db_api = workflow_api.rsplit("/run", 1)[0] + "/db/execute"
    sql = (
        "SELECT id, user_id, phone, license_plate, created_at "
        "FROM case_records "
        f"WHERE user_id = '{escape_sql_literal(workflow_user_id)}' "
        "ORDER BY created_at DESC LIMIT 5;"
    )

    try:
        resp = requests.post(
            db_api,
            headers={
                "Authorization": f"Bearer {workflow_token}",
                "Content-Type": "application/json",
            },
            json={"sql": sql},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return {
                "checked": True,
                "status": "FAILED",
                "reason": f"DB API HTTP {resp.status_code}",
                "found": False,
                "records": [],
            }
        data = resp.json().get("data", {})
        rows = data.get("rows", []) or []
        return {
            "checked": True,
            "status": "PASSED",
            "reason": "查询成功",
            "found": len(rows) > 0,
            "records": rows,
        }
    except Exception as exc:
        return {
            "checked": True,
            "status": "FAILED",
            "reason": f"DB 查询异常: {exc}",
            "found": False,
            "records": [],
        }


def should_force_contact_reply(service_reply: str) -> bool:
    text = service_reply or ""
    return "手机号" in text or "车牌" in text


def should_force_confirm_reply(service_reply: str) -> bool:
    text = service_reply or ""
    return (
        "准确的话回复" in text
        or "确认无误" in text
        or ("确认" in text and "以上信息" in text)
    )


def build_forced_contact_reply(service_reply: str, profile: UserProfile) -> str:
    need_phone = "手机号" in service_reply
    need_plate = "车牌" in service_reply
    if need_phone and need_plate:
        return f"我的手机号是{profile.phone}，车牌号是{profile.license_plate}。"
    if need_phone:
        return f"我的手机号是{profile.phone}。"
    if need_plate:
        return f"我的车牌号是{profile.license_plate}。"
    return f"我的手机号是{profile.phone}，车牌号是{profile.license_plate}。"


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
    def _headers(tok: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {tok}",
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
            headers=_headers(token),
            json=payload,
            stream=True,
            timeout=timeout,
        )
        if response.status_code == 401:
            fresh = read_latest_coze_cli_token()
            if fresh and fresh != token:
                response = requests.post(
                    api_url,
                    headers=_headers(fresh),
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
    def _headers(tok: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {tok}",
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
            headers=_headers(token),
            json=payload,
            timeout=timeout,
        )
        if response.status_code == 401:
            fresh = read_latest_coze_cli_token()
            if fresh and fresh != token:
                response = requests.post(
                    api_url,
                    headers=_headers(fresh),
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
    mail_cfg: MailConfig,
    require_email_check: bool,
    run_id: str,
    profile: UserProfile,
) -> dict[str, Any]:
    print(f"\n{'=' * 72}")
    print(f"场景: {scenario.name} ({scenario.scenario_type})")
    print("=" * 72)
    scenario_start_ts = time.time()

    workflow_user_id = f"{profile.base_user_id}_{run_id}"
    ai_user_session_id = ""
    conversation: list[dict[str, str]] = []
    turn = 0
    exit_reason = "达到最大轮数"

    user_message = profile.complaint_opening
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

        if (
            "工作人员将会尽快处理" in service_reply
            or "1-3个工作日内联系您" in service_reply
        ):
            exit_reason = "工单创建成功"
            break
        if "祝您生活愉快" in service_reply:
            exit_reason = "对话结束"
            break

        if should_force_confirm_reply(service_reply):
            user_message = profile.confirmation_reply
            conversation.append({"role": "user", "content": user_message})
            turn += 1
            print(f"[{turn}] 👤 用户(强制确认): {user_message}")
            time.sleep(0.3)
            continue

        if should_force_contact_reply(service_reply):
            user_message = build_forced_contact_reply(service_reply, profile)
            conversation.append({"role": "user", "content": user_message})
            turn += 1
            print(f"[{turn}] 👤 用户(强制槽位): {user_message}")
            time.sleep(0.3)
            continue

        followup_prompt = (
            f"客服说：{service_reply}\n"
            "请继续按你的场景身份回复。"
            f"注意：手机号必须是 {profile.phone}，车牌号必须是 {profile.license_plate}。"
            "不要使用脱敏格式，不要使用 xxxx。"
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

        user_message = sanitize_message(user_result["reply"])
        if "xxxx" in user_message.lower():
            user_message = (
                f"我的手机号是{profile.phone}，车牌号是{profile.license_plate}。"
            )
        ai_user_session_id = user_result.get("session_id", ai_user_session_id)
        conversation.append({"role": "user", "content": user_message})
        turn += 1
        print(f"[{turn}] 👤 用户: {user_message}")
        time.sleep(0.5)

    result = {
        "success": True,
        "scenario": scenario.name,
        "scenario_type": scenario.scenario_type,
        "total_turns": turn,
        "exit_reason": exit_reason,
        "workflow_user_id": workflow_user_id,
        "conversation": conversation,
    }
    case_check = fetch_case_records_for_user(
        workflow_api=workflow_api,
        workflow_token=workflow_token,
        workflow_user_id=workflow_user_id,
    )
    result["case_check"] = case_check
    case_created = bool(case_check.get("found"))

    should_check_email = case_created and scenario.expect_case_created
    if should_check_email:
        print(f"[邮箱校验] 场景 {scenario.name} 触发兜底，开始拉取收件箱...")
        result["fallback_email_check"] = find_and_validate_fallback_email(
            mail_cfg=mail_cfg,
            workflow_user_id=workflow_user_id,
            scenario_start_ts=scenario_start_ts,
            conversation=conversation,
        )
        check = result["fallback_email_check"]
        print(
            f"[邮箱校验] 状态={check.get('status')} "
            f"命中={check.get('found')} 原因={check.get('reason')}"
        )
    else:
        result["fallback_email_check"] = build_mail_check_result(
            checked=False,
            found=False,
            status="SKIPPED",
            reason="本场景未触发工单兜底，无需校验邮件",
        )

    failure_code = ""
    if scenario.expect_case_created and not case_created:
        failure_code = "NO_CASE_RECORD"
        result["success"] = False
        result["error"] = "未查询到 case_records 工单记录"
    elif should_check_email:
        email_status = (result.get("fallback_email_check") or {}).get("status", "")
        if require_email_check and email_status != "PASSED":
            failure_code = "EMAIL_CHECK_NOT_PASSED"
            result["success"] = False
            result["error"] = "邮件校验未通过"

    if failure_code:
        result["failure_code"] = failure_code

    return result


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
        lines.append(f"- 类型: {item.get('scenario_type')}")
        lines.append(f"- 轮数: {item.get('total_turns', 0)}")
        lines.append(f"- 结束原因: {item.get('exit_reason', '')}")
        lines.append(f"- 客服 user_id: {item.get('workflow_user_id', '')}")
        lines.append(f"- Profile: {item.get('profile_id', '')}")
        if item.get("error"):
            lines.append(f"- 错误: {item.get('error')}")
        if item.get("failure_code"):
            lines.append(f"- 失败码: {item.get('failure_code')}")
        email_check = item.get("fallback_email_check") or {}
        case_check = item.get("case_check") or {}
        lines.append(f"- 邮件校验状态: {email_check.get('status', 'SKIPPED')}")
        lines.append(f"- 工单落库状态: {case_check.get('status', 'SKIPPED')}")
        lines.append("")
        lines.append("### 原始对话记录")
        lines.append("")
        for msg in item.get("conversation", []):
            role = "👤 用户" if msg["role"] == "user" else "🤖 客服"
            lines.append(f"- {role}: {msg['content']}")
        lines.append("")
        lines.append("### 兜底邮件校验")
        lines.append("")
        lines.append(f"- 是否执行: {email_check.get('checked', False)}")
        lines.append(f"- 是否命中: {email_check.get('found', False)}")
        lines.append(f"- 状态: {email_check.get('status', 'SKIPPED')}")
        lines.append(f"- 说明: {email_check.get('reason', '')}")
        if email_check.get("found"):
            lines.append(f"- 命中方式: {email_check.get('matched_by', '')}")
            lines.append(f"- 主题: {email_check.get('subject', '')}")
            lines.append(f"- 时间: {email_check.get('sent_at', '')}")
            lines.append(f"- 发件人: {email_check.get('from_addr', '')}")
            lines.append(f"- 收件人: {email_check.get('to_addr', '')}")
            checks = email_check.get("checks", {})
            if checks:
                for key, value in checks.items():
                    lines.append(f"- 校验 `{key}`: {'✅' if value else '❌'}")
            missing = email_check.get("missing", [])
            if missing:
                lines.append(f"- 缺失项: {', '.join(missing)}")
            lines.append("")
            lines.append("#### 邮件正文（原文摘录）")
            lines.append("")
            lines.append("```text")
            lines.append((email_check.get("body_preview") or "").strip())
            lines.append("```")
        lines.append("")
        lines.append("### 工单落库校验")
        lines.append("")
        lines.append(f"- 是否执行: {case_check.get('checked', False)}")
        lines.append(f"- 是否命中: {case_check.get('found', False)}")
        lines.append(f"- 状态: {case_check.get('status', 'SKIPPED')}")
        lines.append(f"- 说明: {case_check.get('reason', '')}")
        records = case_check.get("records", [])
        if records:
            for rec in records:
                lines.append(
                    f"- case_id={rec.get('id')} user_id={rec.get('user_id')} "
                    f"phone={rec.get('phone')} plate={rec.get('license_plate')} "
                    f"created_at={rec.get('created_at')}"
                )
        lines.append("")

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI User Agent 集成测试")
    parser.add_argument("--max-turns", type=int, default=8, help="每个场景最大轮数")
    parser.add_argument(
        "--profiles",
        type=str,
        default="src/tests/testdata/user_profiles.json",
        help="测试用户档案配置文件路径",
    )
    parser.add_argument("--run-id", type=str, default="", help="本次测试 run_id（可选）")
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
        mail_cfg = load_mail_config()
        profiles = load_user_profiles(args.profiles)
        run_id = args.run_id.strip() or datetime.now().strftime("%Y%m%d%H%M%S")
        require_email_check = os.getenv("REQUIRE_EMAIL_CHECK", "true").strip().lower() in {
            "1",
            "true",
            "yes",
        }
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
        if scenario.scenario_type not in profiles:
            results.append(
                {
                    "success": False,
                    "scenario": scenario.name,
                    "scenario_type": scenario.scenario_type,
                    "error": f"缺少 profile: {scenario.scenario_type}",
                    "failure_code": "MISSING_PROFILE",
                }
            )
            continue
        profile = profiles[scenario.scenario_type]
        result = run_scenario(
            scenario=scenario,
            ai_user_api=ai_user_api,
            ai_user_token=ai_user_token,
            ai_user_project_id=ai_user_project_id,
            workflow_api=workflow_api,
            workflow_token=workflow_token,
            max_turns=args.max_turns,
            mail_cfg=mail_cfg,
            require_email_check=require_email_check,
            run_id=run_id,
            profile=profile,
        )
        result["profile_id"] = profile.profile_id
        results.append(result)
        time.sleep(1)

    report_path = save_report(results)
    passed = sum(1 for x in results if x.get("success"))
    email_failed = sum(
        1
        for x in results
        if (x.get("fallback_email_check") or {}).get("status") == "FAILED"
    )
    print(f"\n完成: {passed}/{len(results)} 场景成功")
    if email_failed:
        print(f"邮件校验失败场景: {email_failed}")
    print(f"报告: {report_path}")
    return 0 if passed == len(results) and email_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
