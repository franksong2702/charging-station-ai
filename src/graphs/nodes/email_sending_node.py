"""
邮件发送节点 - 发送用户投诉信息到指定邮箱
支持重试机制，最多重试3次
自动根据端口选择SSL或STARTTLS连接模式
收件邮箱通过配置文件管理
"""
import json
import logging
import os
import smtplib
import ssl
import time
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr, formatdate, make_msgid
from typing import Dict, Any

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_workload_identity import Client
from cozeloop.decorator import observe

from graphs.state import EmailSendingInput, EmailSendingOutput

# 配置日志
logger = logging.getLogger(__name__)

# 重试配置
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_BASE = 2  # 基础延迟秒数

# SSL端口列表（这些端口使用SMTP_SSL直连）
SSL_PORTS = [465, 993, 995]


def get_smtp_config() -> Dict[str, Any]:
    """获取SMTP发件配置信息（从集成管理获取）"""
    client = Client()
    email_credential = client.get_integration_credential("integration-email-imap-smtp")
    return json.loads(email_credential)


def get_recipient_config() -> Dict[str, Any]:
    """
    获取收件邮箱配置（直接从环境变量读取，避免 pydantic 兼容性问题）
    
    Returns:
        Dict[str, Any]: 包含 recipient_emails 和 recipient_name 的字典
    """
    # 从环境变量读取，或者使用默认值
    recipient_email = os.getenv("EMAIL_RECIPIENT", "xuefu.song@qq.com")
    recipient_name = os.getenv("EMAIL_RECIPIENT_NAME", "充电桩客服团队")
    
    # 支持多个邮箱用逗号分隔
    recipient_emails = [email.strip() for email in recipient_email.split(",") if email.strip()]
    
    logger.info(f"使用环境变量配置 - 收件邮箱列表: {recipient_emails}")
    logger.info(f"使用环境变量配置 - 收件人名称: {recipient_name}")
    
    return {
        "recipient_emails": recipient_emails,
        "recipient_name": recipient_name
    }


@observe
def send_complaint_email(
    subject: str,
    content: str,
    to_addrs: list
) -> Dict[str, Any]:
    """
    发送投诉信息邮件（支持重试，自动选择连接模式，支持多个收件人）
    
    Args:
        subject: 邮件主题
        content: 邮件正文（HTML格式）
        to_addrs: 收件人邮箱列表
        
    Returns:
        发送结果字典，包含状态和消息
    """
    try:
        smtp_config = get_smtp_config()
        smtp_server = smtp_config["smtp_server"]
        smtp_port = smtp_config["smtp_port"]
        
        logger.info(f"邮件配置 - 服务器: {smtp_server}, 端口: {smtp_port}")
        logger.info(f"收件人列表: {to_addrs}")
        
        # 创建邮件消息
        msg = MIMEText(content, "html", "utf-8")
        msg["From"] = formataddr(("充电桩智能客服", smtp_config["account"]))
        msg["To"] = ", ".join(to_addrs)  # 多个收件人用逗号分隔
        msg["Subject"] = Header(subject, "utf-8")
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()
        
        # 创建SSL上下文
        ctx = ssl.create_default_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        
        # 重试机制
        last_err = None
        last_attempt = False
        
        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            last_attempt = (attempt == MAX_RETRY_ATTEMPTS)
            
            try:
                logger.info(f"邮件发送尝试 {attempt}/{MAX_RETRY_ATTEMPTS}")
                
                # 根据端口选择连接方式
                if smtp_port in SSL_PORTS:
                    # SSL直连模式（端口465等）
                    logger.info(f"使用SMTP_SSL模式连接 {smtp_server}:{smtp_port}")
                    with smtplib.SMTP_SSL(
                        smtp_server,
                        smtp_port,
                        context=ctx,
                        timeout=30
                    ) as server:
                        server.ehlo()
                        server.login(smtp_config["account"], smtp_config["auth_code"])
                        server.sendmail(smtp_config["account"], to_addrs, msg.as_string())
                else:
                    # STARTTLS模式（端口587等）
                    logger.info(f"使用STARTTLS模式连接 {smtp_server}:{smtp_port}")
                    with smtplib.SMTP(
                        smtp_server,
                        smtp_port,
                        timeout=30
                    ) as server:
                        server.ehlo()
                        server.starttls(context=ctx)
                        server.ehlo()
                        server.login(smtp_config["account"], smtp_config["auth_code"])
                        server.sendmail(smtp_config["account"], to_addrs, msg.as_string())
                
                logger.info(f"邮件发送成功 - 收件人: {', '.join(to_addrs)}")
                return {
                    "status": "success",
                    "message": f"邮件已成功发送至 {', '.join(to_addrs)}",
                    "attempts": attempt,
                    "recipients": to_addrs
                }
                
            except (
                smtplib.SMTPServerDisconnected,
                smtplib.SMTPConnectError,
                smtplib.SMTPDataError,
                smtplib.SMTPHeloError,
                ssl.SSLError,
                OSError,
                TimeoutError
            ) as e:
                last_err = e
                logger.warning(f"邮件发送失败 (尝试 {attempt}/{MAX_RETRY_ATTEMPTS}): {str(e)}")
                
                # 如果不是最后一次尝试，等待后重试
                if not last_attempt:
                    delay = RETRY_DELAY_BASE * attempt  # 递增延迟：2s, 4s, 6s
                    logger.info(f"等待 {delay} 秒后重试...")
                    time.sleep(delay)
        
        # 所有尝试都失败
        if last_err:
            logger.error(f"邮件发送最终失败: {str(last_err)}")
            return {
                "status": "error",
                "message": "发送失败，已重试3次",
                "detail": str(last_err),
                "recipients": to_addrs
            }
        
        return {"status": "error", "message": "发送失败: 未知错误", "recipients": to_addrs}
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"邮件认证失败: {str(e)}")
        return {"status": "error", "message": f"认证失败: {str(e)}", "recipients": to_addrs}
    except smtplib.SMTPRecipientsRefused as e:
        logger.error(f"收件人被拒绝: {str(e)}")
        return {"status": "error", "message": "收件人被拒绝", "recipients": to_addrs}
    except smtplib.SMTPSenderRefused as e:
        logger.error(f"发件人被拒绝: {str(e)}")
        return {"status": "error", "message": f"发件人被拒绝", "recipients": to_addrs}
    except smtplib.SMTPDataError as e:
        logger.error(f"数据被拒绝: {str(e)}")
        return {"status": "error", "message": f"数据被拒绝", "recipients": to_addrs}
    except smtplib.SMTPConnectError as e:
        logger.error(f"连接失败: {str(e)}")
        return {"status": "error", "message": f"连接失败", "recipients": to_addrs}
    except Exception as e:
        logger.error(f"邮件发送异常: {str(e)}")
        return {"status": "error", "message": f"发送失败: {str(e)}", "recipients": to_addrs}


def email_sending_node(
    state: EmailSendingInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> EmailSendingOutput:
    """
    title: 邮件发送
    desc: 将用户问题信息发送到客服邮箱（支持重试，最多3次）
    integrations: 邮件
    """
    # 获取上下文
    ctx = runtime.context
    
    # 获取收件邮箱配置
    recipient_config = get_recipient_config()
    recipient_emails = recipient_config.get("recipient_emails", ["xuefu.song@qq.com"])
    recipient_name = recipient_config.get("recipient_name", "充电桩客服团队")
    
    logger.info(f"邮件发送节点 - 收件人: {recipient_name}, 邮箱列表: {recipient_emails}")
    
    # 优先使用新字段（兜底流程），兼容旧字段（投诉场景）
    phone = state.phone or state.user_info.get("phone", "未知")
    license_plate = state.license_plate or state.user_info.get("license_plate", "无")
    problem_summary = state.problem_summary or state.user_info.get("description", "")
    case_id = state.case_id or "无"
    
    logger.info(f"邮件发送节点 - 手机: {phone}, 车牌: {license_plate}, 工单: {case_id}")
    
    # 构建对话记录 HTML（只展示最近20条，避免历史记录过长）
    conversation_html = ""
    if state.conversation_history:
        # 使用完整对话历史，最多保留最近 20 条
        # 业务说明：邮件需要包含完整的用户对话历史（Round 1 到当前轮次）
        # Round 4（用户确认）不包含新信息，但为了完整性仍然保留
        display_history = state.conversation_history[-20:] if len(state.conversation_history) > 20 else state.conversation_history
        
        conversation_items = []
        for msg in display_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                conversation_items.append(f"""
                    <div style="margin-bottom: 12px;">
                        <span style="background-color: #e3f2fd; padding: 4px 8px; border-radius: 4px; font-weight: bold;">👤 用户：</span>
                        <div style="margin-top: 6px; padding: 10px; background-color: #f5f5f5; border-radius: 8px;">{content}</div>
                    </div>
                """)
            elif role == "assistant":
                conversation_items.append(f"""
                    <div style="margin-bottom: 12px;">
                        <span style="background-color: #e8f5e9; padding: 4px 8px; border-radius: 4px; font-weight: bold;">🤖 AI：</span>
                        <div style="margin-top: 6px; padding: 10px; background-color: #fafafa; border-radius: 8px; border-left: 3px solid #4CAF50;">{content}</div>
                    </div>
                """)
        conversation_html = f"""
            <div class="field">
                <span class="label">💬 完整对话记录：</span>
                <div style="margin-top: 10px; padding: 15px; background-color: #fff; border: 1px solid #e0e0e0; border-radius: 8px; max-height: 400px; overflow-y: auto;">
                    {''.join(conversation_items)}
                </div>
            </div>
        """
    
    # 构建邮件主题（包含工单号，便于内部跟踪）
    subject = f"【充电桩客服】用户问题反馈 - 手机:{phone}"
    if case_id and case_id != "无":
        subject = f"【充电桩客服】用户问题反馈 - 工单:{case_id} 手机:{phone}"
    
    # 构建邮件正文（HTML格式）
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .container {{ padding: 20px; background-color: #f9f9f9; }}
            .header {{ background-color: #4CAF50; color: white; padding: 10px; text-align: center; }}
            .content {{ background-color: white; padding: 20px; margin-top: 20px; }}
            .field {{ margin-bottom: 15px; }}
            .label {{ font-weight: bold; color: #333; }}
            .value {{ color: #666; }}
            .summary {{ margin-top: 10px; padding: 15px; background-color: #e8f5e9; border-left: 4px solid #4CAF50; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>充电桩用户问题反馈</h2>
            </div>
            <div class="content">
                <div class="field">
                    <span class="label">📋 工单编号：</span>
                    <span class="value">{case_id}</span>
                </div>
                <div class="field">
                    <span class="label">📱 手机号：</span>
                    <span class="value">{phone}</span>
                </div>
                <div class="field">
                    <span class="label">🚗 车牌号：</span>
                    <span class="value">{license_plate}</span>
                </div>
                <div class="field">
                    <span class="label">📝 问题总结：</span>
                    <div class="value summary">
                        {problem_summary if problem_summary else state.user_message}
                    </div>
                </div>
                {conversation_html}
            </div>
            <div style="text-align: center; padding: 10px; color: #999; font-size: 12px;">
                此邮件由充电桩智能客服系统自动发送 | 时间：{formatdate(localtime=True)}
            </div>
        </div>
    </body>
    </html>
    """
    
    # 发送邮件（带重试，支持多个收件人）
    result = send_complaint_email(
        subject=subject,
        content=html_content,
        to_addrs=recipient_emails
    )
    
    # 判断是否发送成功（用于内部日志）
    email_sent = result.get("status") == "success"
    
    if email_sent:
        logger.info("邮件发送成功")
    else:
        # 记录详细错误日志，但不暴露给用户
        error_detail = result.get("detail", result.get("message", "未知错误"))
        logger.error(f"邮件发送失败（已记录，不暴露给用户）: {error_detail}")
    
    # 【重要】无论邮件是否发送成功，都返回统一的友好提示
    # 工单已经创建成功，用户不需要知道邮件发送的技术细节
    # 优先使用传入的 reply_content，如果没有则使用默认的
    reply_content = state.reply_content or """✅ 收到您的问题，我们的工作人员将会尽快处理，并在1-3个工作日内联系您。

如有其他问题，随时可以问我。"""
    
    return EmailSendingOutput(
        email_sent=email_sent,
        reply_content=reply_content
    )
