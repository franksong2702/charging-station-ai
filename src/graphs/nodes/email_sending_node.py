"""
邮件发送节点 - 发送用户投诉信息到指定邮箱
支持重试机制，最多重试3次
"""
import json
import logging
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

# 收件邮箱（客服邮箱）
RECIPIENT_EMAIL = "xuefu.song@qq.com"

# 重试配置
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_BASE = 2  # 基础延迟秒数


def get_email_config() -> Dict[str, Any]:
    """获取邮件配置信息"""
    client = Client()
    email_credential = client.get_integration_credential("integration-email-imap-smtp")
    return json.loads(email_credential)


@observe
def send_complaint_email(
    subject: str,
    content: str,
    to_addr: str
) -> Dict[str, Any]:
    """
    发送投诉信息邮件（支持重试）
    
    Args:
        subject: 邮件主题
        content: 邮件正文（HTML格式）
        to_addr: 收件人邮箱
        
    Returns:
        发送结果字典，包含状态和消息
    """
    try:
        config = get_email_config()
        
        # 创建邮件消息
        msg = MIMEText(content, "html", "utf-8")
        msg["From"] = formataddr(("充电桩智能客服", config["account"]))
        msg["To"] = to_addr
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
                
                with smtplib.SMTP_SSL(
                    config["smtp_server"],
                    config["smtp_port"],
                    context=ctx,
                    timeout=30
                ) as server:
                    server.ehlo()
                    server.login(config["account"], config["auth_code"])
                    server.sendmail(config["account"], [to_addr], msg.as_string())
                    server.quit()
                
                logger.info(f"邮件发送成功 - 收件人: {to_addr}")
                return {
                    "status": "success",
                    "message": f"邮件已成功发送至 {to_addr}",
                    "attempts": attempt
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
                "detail": str(last_err)
            }
        
        return {"status": "error", "message": "发送失败: 未知错误"}
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"邮件认证失败: {str(e)}")
        return {"status": "error", "message": f"认证失败: {str(e)}"}
    except smtplib.SMTPRecipientsRefused as e:
        logger.error(f"收件人被拒绝: {str(e)}")
        return {"status": "error", "message": "收件人被拒绝"}
    except smtplib.SMTPSenderRefused as e:
        logger.error(f"发件人被拒绝: {str(e)}")
        return {"status": "error", "message": f"发件人被拒绝"}
    except smtplib.SMTPDataError as e:
        logger.error(f"数据被拒绝: {str(e)}")
        return {"status": "error", "message": f"数据被拒绝"}
    except smtplib.SMTPConnectError as e:
        logger.error(f"连接失败: {str(e)}")
        return {"status": "error", "message": f"连接失败: {str(e)}"}
    except Exception as e:
        logger.error(f"邮件发送异常: {str(e)}")
        return {"status": "error", "message": f"发送失败: {str(e)}"}


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
    
    # 优先使用新字段（兜底流程），兼容旧字段（投诉场景）
    phone = state.phone or state.user_info.get("phone", "未知")
    license_plate = state.license_plate or state.user_info.get("license_plate", "无")
    problem_summary = state.problem_summary or state.user_info.get("description", "")
    case_id = state.case_id or "无"
    
    logger.info(f"邮件发送节点 - 手机: {phone}, 车牌: {license_plate}, 工单: {case_id}")
    
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
                <div class="field">
                    <span class="label">💬 用户原始消息：</span>
                    <div class="value" style="margin-top: 10px; padding: 10px; background-color: #fff3cd; border-left: 4px solid #ffc107;">
                        {state.user_message}
                    </div>
                </div>
            </div>
            <div style="text-align: center; padding: 10px; color: #999; font-size: 12px;">
                此邮件由充电桩智能客服系统自动发送 | 时间：{formatdate(localtime=True)}
            </div>
        </div>
    </body>
    </html>
    """
    
    # 发送邮件（带重试）
    result = send_complaint_email(
        subject=subject,
        content=html_content,
        to_addr=RECIPIENT_EMAIL
    )
    
    # 判断是否发送成功
    email_sent = result.get("status") == "success"
    
    # 生成回复（不向用户展示工单号）
    if email_sent:
        logger.info("邮件发送成功")
        reply_content = """✅ 您的问题已成功提交！

我们的工作人员会在24小时内联系您处理，请保持电话畅通。

如有其他问题，随时可以问我。"""
    else:
        error_msg = result.get("message", "未知错误")
        logger.error(f"邮件发送失败: {error_msg}")
        reply_content = f"""⚠️ 信息提交失败：{error_msg}

请直接联系客服电话：400-XXX-XXXX

我们会尽快为您处理。"""
    
    return EmailSendingOutput(
        email_sent=email_sent,
        reply_content=reply_content
    )
