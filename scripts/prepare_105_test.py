#!/usr/bin/env python
"""
知识库 105 个问题完整测试
"""
import sys
import os
import json
import time
import pandas as pd

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def load_knowledge_questions():
    """从 Excel 加载 105 个问题"""
    df = pd.read_excel('assets/知识库-更多一点.xlsx')
    kb_df = df[df['ID'].astype(str).str.startswith('KB', na=False)].reset_index(drop=True)
    return kb_df


def main():
    print("=" * 80)
    print("知识库 105 个问题完整测试")
    print("=" * 80)
    print()
    
    kb_df = load_knowledge_questions()
    print(f"共加载 {len(kb_df)} 个问题")
    print()
    
    # 保存完整问题列表
    results = []
    for i, row in kb_df.iterrows():
        results.append({
            "id": row['ID'],
            "category": row['分类'],
            "sub_category": row['子分类'],
            "question": row['问题'],
            "short_answer": row['简短回答'],
            "detailed_answer": row['详细回答'],
            "keywords": row['关键词'],
            "status": "pending"
        })
    
    with open('assets/all_105_questions.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("=" * 80)
    print(f"完整问题清单已保存至: assets/all_105_questions.json")
    print(f"共 {len(results)} 个问题")
    print()
    print("问题分类统计:")
    category_count = kb_df['分类'].value_counts()
    for category, count in category_count.items():
        print(f"  - {category}: {count} 题")
    print()
    print("请使用 test_run 工具逐一验证！")
    print("=" * 80)


if __name__ == '__main__':
    main()
