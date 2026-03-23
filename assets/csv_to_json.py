#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV知识库转换工具
功能：将CSV格式的知识库转换为JSON格式，供智能客服系统使用

使用方法：
    python csv_to_json.py input.csv output.json
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


def parse_pipe_separated(value: str) -> List[str]:
    """
    解析用竖线分隔的字符串，返回列表
    
    Args:
        value: 用|分隔的字符串，如 "特斯拉|扫码|二维码"
    
    Returns:
        列表，如 ["特斯拉", "扫码", "二维码"]
    """
    if not value or not value.strip():
        return []
    
    return [item.strip() for item in value.split('|') if item.strip()]


def parse_int(value: str, default: int = 2) -> int:
    """
    解析整数，失败则返回默认值
    
    Args:
        value: 字符串形式的整数
        default: 默认值
    
    Returns:
        整数值
    """
    try:
        return int(value.strip())
    except (ValueError, AttributeError):
        return default


def csv_to_json(csv_path: str, json_path: Optional[str] = None) -> Dict[str, Any]:
    """
    将CSV文件转换为JSON格式的知识库
    
    Args:
        csv_path: CSV文件路径
        json_path: 输出JSON文件路径（可选）
    
    Returns:
        知识库数据结构
    """
    csv_file = Path(csv_path)
    
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV文件不存在: {csv_path}")
    
    knowledge_base: List[Dict[str, Any]] = []
    stats = {
        "total": 0,
        "by_category": {},
        "errors": []
    }
    
    # 读取CSV文件
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):  # 从第2行开始（第1行是标题）
            try:
                # 跳过空行
                if not any(row.values()):
                    continue
                
                # 解析分类
                category = row.get('分类', '').strip()
                if not category:
                    stats["errors"].append(f"第{row_num}行: 缺少分类")
                    continue
                
                # 解析关键词和标签
                keywords = parse_pipe_separated(row.get('关键词', ''))
                tags = parse_pipe_separated(row.get('标签', ''))
                
                # 构建知识条目
                entry = {
                    "id": row.get('ID', '').strip() or f"KB{row_num:03d}",
                    "category": category,
                    "subcategory": row.get('子分类', '').strip(),
                    "question": row.get('问题', '').strip(),
                    "short_answer": row.get('简短回答', '').strip(),
                    "detailed_answer": row.get('详细回答', '').strip(),
                    "keywords": keywords,
                    "tags": tags,
                    "priority": parse_int(row.get('优先级', '2'), 2),
                    "related_questions": parse_pipe_separated(row.get('关联问题ID', '')),
                    "notes": row.get('备注', '').strip()
                }
                
                # 验证必填字段
                if not entry["question"]:
                    stats["errors"].append(f"第{row_num}行: 缺少问题")
                    continue
                
                if not entry["short_answer"]:
                    stats["errors"].append(f"第{row_num}行: 缺少简短回答")
                    continue
                
                # 添加到知识库
                knowledge_base.append(entry)
                
                # 更新统计
                stats["total"] += 1
                stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
                
            except Exception as e:
                stats["errors"].append(f"第{row_num}行: 处理错误 - {str(e)}")
    
    # 构建完整的知识库结构
    result = {
        "metadata": {
            "version": "1.0.0",
            "name": "充电桩智能客服知识库",
            "description": "从CSV导入的知识库",
            "updated_at": datetime.now().strftime("%Y-%m-%d"),
            "total_entries": stats["total"],
            "categories": list(stats["by_category"].keys())
        },
        "knowledge_base": knowledge_base
    }
    
    # 保存JSON文件
    if json_path:
        json_file = Path(json_path)
        json_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 知识库已保存到: {json_path}")
    
    # 打印统计信息
    print("\n" + "="*50)
    print("📊 导入统计")
    print("="*50)
    print(f"总条目数: {stats['total']}")
    print("\n按分类统计:")
    for cat, count in stats["by_category"].items():
        print(f"  - {cat}: {count}条")
    
    if stats["errors"]:
        print(f"\n⚠️ 发现 {len(stats['errors'])} 个问题:")
        for error in stats["errors"][:10]:  # 最多显示10个
            print(f"  - {error}")
        if len(stats["errors"]) > 10:
            print(f"  ... 还有 {len(stats['errors']) - 10} 个问题")
    
    print("="*50 + "\n")
    
    return result


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python csv_to_json.py <input.csv> [output.json]")
        print("\n示例:")
        print("  python csv_to_json.py 知识库填写模板.csv")
        print("  python csv_to_json.py 知识库填写模板.csv 充电桩知识库.json")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    json_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 默认输出路径
    if not json_path:
        json_path = "assets/充电桩知识库_导入.json"
    
    try:
        csv_to_json(csv_path, json_path)
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
