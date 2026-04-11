from sqlalchemy import BigInteger, DateTime, Identity, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, List, Dict, Any
import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ==================== 对话历史表 ====================

class ConversationHistory(Base):
    """对话历史表 - 存储用户对话历史和兜底流程状态"""
    __tablename__ = "conversation_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="用户身份标识")
    user_message: Mapped[str] = mapped_column(Text, nullable=False, comment="用户发送的消息")
    reply_content: Mapped[str] = mapped_column(Text, nullable=False, comment="AI回复内容")
    intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="意图类型")
    fallback_phase: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="兜底流程阶段")
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="手机号")
    license_plate: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="车牌号")
    problem_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="问题总结")
    entry_problem: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="进入兜底时的问题描述")
    user_supplement: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="用户补充信息")
    conversation_truncate_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0, comment="对话截断索引")
    case_confirmed: Mapped[bool] = mapped_column(default=False, comment="用户是否已确认问题总结")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        Index("ix_conversation_history_user_id", "user_id"),
        Index("ix_conversation_history_created_at", "created_at"),
        Index("ix_conversation_history_user_created", "user_id", "created_at"),
    )


class DialogRecord(Base):
    """对话记录表 - 存储有价值的对话记录（评价、不满意、知识库缺失）"""
    __tablename__ = "dialog_records"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, comment="用户ID")
    user_message: Mapped[str] = mapped_column(Text, nullable=False, comment="用户消息")
    reply_content: Mapped[str] = mapped_column(Text, nullable=False, comment="回复内容")
    intent: Mapped[str] = mapped_column(String(50), nullable=False, comment="意图类型")
    feedback_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="反馈类型")
    knowledge_matched: Mapped[bool] = mapped_column(default=False, comment="是否匹配到知识库")
    record_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="记录类型")
    knowledge_chunks: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, comment="相关知识片段")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        Index("ix_dialog_records_user_id", "user_id"),
        Index("ix_dialog_records_created_at", "created_at"),
        Index("ix_dialog_records_record_type", "record_type"),
    )


class CaseRecord(Base):
    """工单记录表 - 存储兜底场景的工单记录"""
    __tablename__ = "case_records"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, comment="用户ID")
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="手机号")
    license_plate: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="车牌号")
    problem_summary: Mapped[str] = mapped_column(Text, nullable=False, comment="问题总结")
    conversation_context: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, comment="对话上下文")
    case_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="工单类型")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", comment="工单状态")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    __table_args__ = (
        Index("ix_case_records_user_id", "user_id"),
        Index("ix_case_records_created_at", "created_at"),
        Index("ix_case_records_status", "status"),
    )
