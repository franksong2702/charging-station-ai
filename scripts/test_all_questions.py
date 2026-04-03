#!/usr/bin/env python
"""
知识库 105 个问题完整测试
"""
import sys
import os
import json
import pandas as pd

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from coze_coding_dev_sdk import LLMClient, Config
from coze_coding_dev_sdk import KnowledgeClient
from langchain_core.messages import SystemMessage, HumanMessage
from jinja2 import Template


def load_knowledge_questions():
    """从 Excel 加载 105 个问题"""
    df = pd.read_excel('assets/知识库-更多一点.xlsx')
    kb_df = df[df['ID'].astype(str).str.startswith('KB', na=False)].reset_index(drop=True)
    return kb_df


def test_single_question(question, short_answer, detailed_answer):
    """测试单个问题"""
    from coze_coding_dev_sdk import LLMClient, Config
    from langchain_core.messages import SystemMessage, HumanMessage
    
    # 这是简化的测试，实际工作流需要通过 test_run 调用
    # 这里我们直接打印问题，等待人工验证
    return {
        "question": question,
        "short_answer": short_answer,
        "detailed_answer": detailed_answer,
        "status": "need_verify"
    }


def main():
    print("=" * 80)
    print("知识库 105 个问题完整测试")
    print("=" * 80)
    print()
    
    kb_df = load_knowledge_questions()
    print(f"共加载 {len(kb_df)} 个问题")
    print()
    
    # 打印所有问题和预期回答
    results = []
    for i, row in kb_df.iterrows():
        print(f"--- 问题 {i+1} / {len(kb_df)} ---")
        print(f"问题: {row['问题']}")
        print(f"预期简短回答: {row['简短回答']}")
        print()
        
        results.append({
            "id": row['ID'],
            "category": row['分类'],
            "sub_category": row['子分类'],
            "question": row['问题'],
            "short_answer": row['简短回答'],
            "detailed_answer": row['详细回答'],
            "keywords": row['关键词']
        })
    
    # 保存测试清单
    with open('assets/test_questions_list.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print()
    print("=" * 80)
    print(f"测试清单已保存至: assets/test_questions_list.json")
    print("共 {len(results)} 个问题")
    print("=" * 80)


if __name__ == '__main__':
    main()
