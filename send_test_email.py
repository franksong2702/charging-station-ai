#!/usr/bin/env python3
"""
测试邮件发送脚本 - 直接发送一封测试邮件
"""
import sys
import os

# 设置项目路径和PYTHONPATH
project_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
src_path = os.path.join(project_path, "src")
sys.path.insert(0, src_path)
sys.path.insert(0, project_path)

print(f"[DEBUG] Project path: {project_path}")
print(f"[DEBUG] Src path: {src_path}")
print(f"[DEBUG] Sys path: {sys.path[:5]}")

from graphs.nodes.email_sending_node import send_complaint_email

def main():
    print("🚀 开始发送测试邮件...")
    
    subject = "【充电桩客服】测试邮件 - 工单创建测试"
    content = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; }
            .container { padding: 20px; background-color: #f9f9f9; }
            .header { background-color: #4CAF50; color: white; padding: 10px; text-align: center; }
            .content { background-color: white; padding: 20px; margin-top: 20px; }
            .field { margin-bottom: 15px; }
            .label { font-weight: bold; color: #333; }
            .value { color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>充电桩用户问题反馈 - 测试邮件</h2>
            </div>
            <div class="content">
                <div class="field">
                    <span class="label">📋 工单编号：</span>
                    <span class="value">TEST-001</span>
                </div>
                <div class="field">
                    <span class="label">📱 手机号：</span>
                    <span class="value">13912345678</span>
                </div>
                <div class="field">
                    <span class="label">🚗 车牌号：</span>
                    <span class="value">京A12345</span>
                </div>
                <div class="field">
                    <span class="label">📝 问题总结：</span>
                    <div class="value summary">
                        充电桩坏了，充不进去电，测试邮件发送功能
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    to_addrs = ["xuefu.song@qq.com"]
    
    print(f"📧 收件人: {to_addrs}")
    print(f"📋 主题: {subject}")
    
    result = send_complaint_email(
        subject=subject,
        content=content,
        to_addrs=to_addrs
    )
    
    print(f"\n📊 发送结果: {result.get('status')}")
    print(f"💬 消息: {result.get('message')}")
    
    if result.get('status') == 'success':
        print("\n✅ 测试邮件发送成功！")
    else:
        print("\n❌ 测试邮件发送失败")
        print(f"   详情: {result}")

if __name__ == "__main__":
    main()
