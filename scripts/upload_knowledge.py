#!/usr/bin/env python
"""
知识库文档上传脚本
用法: python scripts/upload_knowledge.py
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from coze_coding_dev_sdk import KnowledgeClient, Config
from coze_coding_dev_sdk.knowledge.models import KnowledgeDocument, DataSourceType

# 知识库配置
KNOWLEDGE_TABLE_NAME = "charging_station_kb"  # 数据集名称
KNOWLEDGE_FILE = "assets/充电桩知识库.md"      # 本地知识库文件


def upload_knowledge():
    """上传知识库文档到平台"""
    
    # 获取项目根目录
    project_root = os.getenv("COZE_WORKSPACE_PATH", os.path.dirname(os.path.dirname(__file__)))
    knowledge_file_path = os.path.join(project_root, KNOWLEDGE_FILE)
    
    # 读取知识库文件内容
    print(f"📖 读取知识库文件: {knowledge_file_path}")
    
    with open(knowledge_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"✅ 文件内容长度: {len(content)} 字符")
    
    # 初始化知识库客户端
    # 注意：需要在运行时环境中，SDK 会自动获取认证信息
    client = KnowledgeClient(config=Config())
    
    # 创建文档对象
    document = KnowledgeDocument(
        source=DataSourceType.TEXT,
        raw_data=content
    )
    
    # 上传到知识库
    print(f"\n📤 上传到知识库: {KNOWLEDGE_TABLE_NAME}")
    
    try:
        response = client.add_documents(
            documents=[document],
            table_name=KNOWLEDGE_TABLE_NAME
        )
        
        print(f"\n✅ 上传成功!")
        print(f"   文档ID: {response.doc_ids}")
        print(f"   状态: {response}")
        
    except Exception as e:
        print(f"\n❌ 上传失败: {e}")
        raise


if __name__ == "__main__":
    upload_knowledge()
