"""
邮件发送节点 - 发送用户投诉信息到指定邮箱
"""
import json
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


# 收件邮箱（客服邮箱）
RECIPIENT_EMAIL = "xuefu.song@qq.com"


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
    发送投诉信息邮件
    
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
        attempts = 3
        last_err = None
        
        for i in range(attempts):
            try:
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
                
                return {
                    "status": "success",
                    "message": f"邮件已成功发送至 {to_addr}"
                }
                
            except (
                smtplib.SMTPServerDisconnected,
                smtplib.SMTPConnectError,
                smtplib.SMTPDataError,
                smtplib.SMTPHeloError,
                ssl.SSLError,
                OSError
            ) as e:
                last_err = e
                time.sleep(1 * (i + 1))
        
        if last_err:
            return {
                "status": "error",
                "message": "发送失败",
                "detail": str(last_err)
            }
        
        return {"status": "error", "message": "发送失败: 未知错误"}
        
    except smtplib.SMTPAuthenticationError as e:
        return {"status": "error", "message": f"认证失败: {str(e)}"}
    except smtplib.SMTPRecipientsRefused as e:
        return {"status": "error", "message": "收件人被拒绝"}
    except smtplib.SMTPSenderRefused as e:
        return {"status": "error", "message": f"发件人被拒绝"}
    except smtplib.SMTPDataError as e:
        return {"status": "error", "message": f"数据被拒绝"}
    except smtplib.SMTPConnectError as e:
        return {"status": "error", "message": f"连接失败: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"发送失败: {str(e)}"}


def email_sending_node(
    state: EmailSendingInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> EmailSendingOutput:
    """
    title: 邮件发送
    desc: 将用户问题信息发送到客服邮箱（支持兜底流程和投诉场景）
    integrations: 邮件
    """
    # 获取上下文
    ctx = runtime.context
    
    # 优先使用新字段（兜底流程），兼容旧字段（投诉场景）
    phone = state.phone or state.user_info.get("phone", "未知")
    license_plate = state.license_plate or state.user_info.get("license_plate", "无")
    problem_summary = state.problem_summary or state.user_info.get("description", "")
    case_id = state.case_id or "无"
    
    # 构建邮件主题
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
    
    # 发送邮件
    result = send_complaint_email(
        subject=subject,
        content=html_content,
        to_addr=RECIPIENT_EMAIL
    )
    
    # 判断是否发送成功
    email_sent = result.get("status") == "success"
    
    # 生成回复
    if email_sent:
        reply_content = f"""✅ 您的问题已成功提交！

📋 工单编号：{case_id}

我们的工作人员会在24小时内联系您处理，请保持电话畅通。"""
    else:
        reply_content = f"⚠️ 信息提交失败：{result.get('message', '未知错误')}\n\n请直接联系客服电话：400-XXX-XXXX"
    
    return EmailSendingOutput(
        email_sent=email_sent,
        reply_content=reply_content
    )
