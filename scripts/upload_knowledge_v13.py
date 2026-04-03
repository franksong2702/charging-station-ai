
#!/usr/bin/env python
"""
知识库v1.3上传脚本
用法: python scripts/upload_knowledge_v13.py
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from coze_coding_dev_sdk import KnowledgeClient, Config
from coze_coding_dev_sdk.knowledge.models import KnowledgeDocument, DataSourceType, ChunkConfig

# 知识库配置 - v1.3版本
KNOWLEDGE_TABLE_NAME = "charging_station_kb_v1_3"
KNOWLEDGE_FILE = "assets/充电桩知识库_v1.3.md"


def upload_knowledge():
    """上传知识库文档到平台"""
    
    # 获取项目根目录
    project_root = os.getenv("COZE_WORKSPACE_PATH", os.path.dirname(os.path.dirname(__file__)))
    knowledge_file_path = os.path.join(project_root, KNOWLEDGE_FILE)
    
    # 读取知识库文件内容
    print(f"📖 读取知识库文件: {knowledge_file_path}")
    
    with open(knowledge_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 统计文件内容
    question_count = content.count('#### ')
    chunk_count = len(content.split('\n\n---\n\n'))
    
    print(f"✅ 文件内容长度: {len(content)} 字符")
    print(f"   问题条目数: {question_count}")
    print(f"   分片数量: {chunk_count}")
    
    # 初始化知识库客户端
    client = KnowledgeClient(config=Config())
    
    # 创建文档对象
    document = KnowledgeDocument(
        source=DataSourceType.TEXT,
        raw_data=content
    )
    
    # 配置分片参数：使用分隔符分割，确保每个问题独立成片
    chunk_config = ChunkConfig(
        separator="\n\n---\n\n",  # 使用分隔符作为分片边界
        max_tokens=2000,          # 每个片段最大 token 数
        remove_extra_spaces=False,
        remove_urls_emails=False
    )
    
    # 上传到知识库
    print(f"\n📤 上传到新数据集: {KNOWLEDGE_TABLE_NAME}")
    print(f"   分片配置: separator='---', max_tokens=2000")
    
    try:
        response = client.add_documents(
            documents=[document],
            table_name=KNOWLEDGE_TABLE_NAME,
            chunk_config=chunk_config
        )
        
        print(f"\n✅ 上传成功!")
        print(f"   文档ID: {response.doc_ids}")
        print(f"   提示: 文档正在异步索引中，请等待几分钟后再测试")
        
    except Exception as e:
        print(f"\n❌ 上传失败: {e}")
        raise


if __name__ == "__main__":
    upload_knowledge()

