from sqlalchemy import BigInteger, DateTime, Identity, Index, Integer, JSON, PrimaryKeyConstraint, String, Text, text, func
from typing import Optional
import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass


# ==================== 对话历史表 ====================

class ConversationHistory(Base):
    """对话历史记录表 - 用于多轮对话上下文"""
    __tablename__ = "conversation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="用户身份标识（企业微信 external_userid）")
    user_message: Mapped[str] = mapped_column(Text, nullable=False, comment="用户发送的消息")
    reply_content: Mapped[str] = mapped_column(Text, nullable=False, comment="AI回复内容")
    intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="意图类型")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")

    __table_args__ = (
        Index("ix_conversation_history_user_id", "user_id"),
        Index("ix_conversation_history_created_at", "created_at"),
        Index("ix_conversation_history_user_created", "user_id", "created_at"),  # 复合索引，用于查询用户历史
    )