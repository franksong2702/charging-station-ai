"""
对话记录保存节点 - 将对话记录保存到JSON文件
"""
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import SaveRecordInput, SaveRecordOutput

# 配置日志
logger = logging.getLogger(__name__)

# 记录文件路径
RECORD_FILE = "assets/dialog_records.json"


def save_record_node(
    state: SaveRecordInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> SaveRecordOutput:
    """
    title: 对话记录保存
    desc: 将对话记录保存到JSON文件，用于后续分析
    integrations: 无
    """
    ctx = runtime.context
    
    # 构建记录对象
    record = {
        "timestamp": datetime.now().isoformat(),
        "user_message": state.user_message,
        "reply_content": state.reply_content,
        "intent": state.intent,
        "feedback_type": state.feedback_type,
        "knowledge_matched": len(state.knowledge_chunks) > 0,
        "knowledge_chunks": [
            {"content": chunk.get("content", "")[:100], "score": chunk.get("score", 0)}
            for chunk in state.knowledge_chunks[:3]  # 只保存前3条
        ]
    }
    
    # 确保目录存在
    record_dir = os.path.join(os.getenv("COZE_WORKSPACE_PATH", ""), "assets")
    os.makedirs(record_dir, exist_ok=True)
    
    record_file = os.path.join(record_dir, "dialog_records.json")
    
    # 读取现有记录
    records = []
    if os.path.exists(record_file):
        try:
            with open(record_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
                if not isinstance(records, list):
                    records = []
        except Exception as e:
            logger.warning(f"读取记录文件失败: {e}")
            records = []
    
    # 追加新记录
    records.append(record)
    
    # 保存文件
    try:
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        logger.info(f"对话记录已保存，总记录数: {len(records)}")
    except Exception as e:
        logger.error(f"保存记录文件失败: {e}")
        return SaveRecordOutput(saved=False)
    
    return SaveRecordOutput(saved=True)
