"""
统一配置管理模块
集中管理项目所有配置，支持环境变量和配置文件
"""
import os
import json
from typing import List, Optional
from pydantic import BaseSettings, Field


class AppConfig(BaseSettings):
    """应用统一配置"""
    
    # ==================== 数据库配置 ====================
    database_url: Optional[str] = Field(None, description="数据库连接 URL")
    
    # ==================== 邮件配置 ====================
    email_recipient: Optional[str] = Field(None, description="收件邮箱地址（多个用逗号分隔）")
    email_recipient_name: str = Field("充电桩客服团队", description="收件人名称")
    email_recipient_2: Optional[str] = Field(None, description="第二个收件邮箱（向后兼容）")
    
    # ==================== LLM 配置 ====================
    llm_provider: str = Field("doubao", description="LLM 提供商：doubao")
    default_model: str = Field("doubao-seed-1-8-251228", description="默认模型 ID")
    
    # ==================== 工作流配置 ====================
    max_history_rounds: int = Field(10, description="最大保留的对话轮数")
    fallback_state_expire_minutes: int = Field(30, description="兜底流程状态过期时间（分钟）")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
config = AppConfig()


def get_email_recipient_emails() -> List[str]:
    """
    获取收件邮箱列表
    
    Returns:
        List[str]: 收件邮箱列表
    """
    recipient_emails = []
    
    # 从统一配置读取
    if config.email_recipient:
        # 支持多个邮箱用逗号分隔
        email_list = [email.strip() for email in config.email_recipient.split(",") if email.strip()]
        recipient_emails.extend(email_list)
    
    # 第二个邮箱（向后兼容）
    if config.email_recipient_2:
        recipient_emails.append(config.email_recipient_2.strip())
    
    # 如果配置为空，使用默认值
    if not recipient_emails:
        recipient_emails = ["xuefu.song@qq.com"]
    
    return recipient_emails


def get_email_recipient_name() -> str:
    """
    获取收件人名称
    
    Returns:
        str: 收件人名称
    """
    return config.email_recipient_name
