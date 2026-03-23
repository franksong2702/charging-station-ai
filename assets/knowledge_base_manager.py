#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
充电桩客服知识库管理工具
功能：添加、查询、更新、删除、导出知识库条目
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class KnowledgeBaseManager:
    """知识库管理器"""
    
    def __init__(self, kb_path: str = "assets/充电桩知识库_结构化.json"):
        """
        初始化知识库管理器
        
        Args:
            kb_path: 知识库JSON文件路径
        """
        self.kb_path = Path(kb_path)
        self.data = self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """加载知识库"""
        if not self.kb_path.exists():
            # 创建空的知识库结构
            return {
                "metadata": {
                    "version": "1.0.0",
                    "name": "充电桩智能客服知识库",
                    "updated_at": datetime.now().strftime("%Y-%m-%d"),
                    "categories": ["使用指导", "故障处理", "计费问题", "安全须知", "其他问题"],
                    "total_entries": 0
                },
                "knowledge_base": []
            }
        
        with open(self.kb_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_knowledge_base(self) -> None:
        """保存知识库"""
        # 更新元数据
        self.data["metadata"]["updated_at"] = datetime.now().strftime("%Y-%m-%d")
        self.data["metadata"]["total_entries"] = len(self.data["knowledge_base"])
        
        # 确保目录存在
        self.kb_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.kb_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        print(f"✅ 知识库已保存到: {self.kb_path}")
    
    def _generate_id(self) -> str:
        """生成知识条目ID"""
        existing_ids = [item.get("id", "") for item in self.data["knowledge_base"]]
        num = len(existing_ids) + 1
        while f"KB{num:03d}" in existing_ids:
            num += 1
        return f"KB{num:03d}"
    
    def add_entry(
        self,
        category: str,
        question: str,
        short_answer: str,
        detailed_answer: str,
        subcategory: str = "",
        keywords: List[str] = None,
        tags: List[str] = None,
        priority: int = 2,
        related_questions: List[str] = None,
        error_codes: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        添加知识条目
        
        Args:
            category: 主分类
            question: 问题
            short_answer: 简短回答
            detailed_answer: 详细回答
            subcategory: 子分类
            keywords: 关键词列表
            tags: 标签列表
            priority: 优先级(1-3, 1最高)
            related_questions: 关联问题ID列表
            error_codes: 错误代码列表
        
        Returns:
            新创建的知识条目
        """
        entry = {
            "id": self._generate_id(),
            "category": category,
            "subcategory": subcategory,
            "keywords": keywords or [],
            "question": question,
            "short_answer": short_answer,
            "detailed_answer": detailed_answer,
            "related_questions": related_questions or [],
            "tags": tags or [],
            "priority": priority
        }
        
        if error_codes:
            entry["error_codes"] = error_codes
        
        self.data["knowledge_base"].append(entry)
        self._save_knowledge_base()
        
        print(f"✅ 已添加知识条目: {entry['id']} - {question}")
        return entry
    
    def search(
        self,
        query: str = "",
        category: str = "",
        subcategory: str = "",
        keywords: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索知识条目
        
        Args:
            query: 搜索关键词（在问题和答案中搜索）
            category: 按分类筛选
            subcategory: 按子分类筛选
            keywords: 按关键词筛选
        
        Returns:
            匹配的知识条目列表
        """
        results = []
        
        for entry in self.data["knowledge_base"]:
            # 分类筛选
            if category and entry.get("category") != category:
                continue
            
            if subcategory and entry.get("subcategory") != subcategory:
                continue
            
            # 关键词筛选
            if keywords:
                entry_keywords = entry.get("keywords", [])
                if not any(kw in entry_keywords for kw in keywords):
                    continue
            
            # 文本搜索
            if query:
                query_lower = query.lower()
                searchable_text = " ".join([
                    entry.get("question", ""),
                    entry.get("short_answer", ""),
                    " ".join(entry.get("keywords", []))
                ]).lower()
                
                if query_lower not in searchable_text:
                    continue
            
            results.append(entry)
        
        return results
    
    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个知识条目
        
        Args:
            entry_id: 条目ID
        
        Returns:
            知识条目或None
        """
        for entry in self.data["knowledge_base"]:
            if entry.get("id") == entry_id:
                return entry
        return None
    
    def update_entry(self, entry_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        更新知识条目
        
        Args:
            entry_id: 条目ID
            updates: 要更新的字段
        
        Returns:
            更新后的知识条目或None
        """
        for i, entry in enumerate(self.data["knowledge_base"]):
            if entry.get("id") == entry_id:
                # 更新字段（保留ID）
                entry_id_original = entry.get("id")
                entry.update(updates)
                entry["id"] = entry_id_original
                
                self.data["knowledge_base"][i] = entry
                self._save_knowledge_base()
                
                print(f"✅ 已更新知识条目: {entry_id}")
                return entry
        
        print(f"❌ 未找到知识条目: {entry_id}")
        return None
    
    def delete_entry(self, entry_id: str) -> bool:
        """
        删除知识条目
        
        Args:
            entry_id: 条目ID
        
        Returns:
            是否删除成功
        """
        for i, entry in enumerate(self.data["knowledge_base"]):
            if entry.get("id") == entry_id:
                self.data["knowledge_base"].pop(i)
                self._save_knowledge_base()
                print(f"✅ 已删除知识条目: {entry_id}")
                return True
        
        print(f"❌ 未找到知识条目: {entry_id}")
        return False
    
    def export_to_markdown(self, output_path: str = "assets/充电桩知识库.md") -> None:
        """
        导出为Markdown格式
        
        Args:
            output_path: 输出文件路径
        """
        md_content = "# 充电桩智能客服知识库\n\n"
        md_content += f"*最后更新: {self.data['metadata']['updated_at']}*\n\n"
        md_content += f"*总条目数: {self.data['metadata']['total_entries']}*\n\n"
        
        # 按分类组织
        categories = {}
        for entry in self.data["knowledge_base"]:
            cat = entry.get("category", "其他")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(entry)
        
        # 生成Markdown
        section_num = 1
        for cat_name, entries in categories.items():
            md_content += f"## {section_num}. {cat_name}\n\n"
            
            for i, entry in enumerate(entries, 1):
                md_content += f"### {section_num}.{i} {entry.get('question', '')}\n\n"
                md_content += f"**关键词**: {', '.join(entry.get('keywords', []))}\n\n"
                md_content += f"**简短回答**: {entry.get('short_answer', '')}\n\n"
                md_content += f"**详细回答**:\n\n{entry.get('detailed_answer', '')}\n\n"
                
                if entry.get('error_codes'):
                    md_content += "**错误代码**:\n\n"
                    md_content += "| 代码 | 描述 | 解决方法 |\n"
                    md_content += "|------|------|----------|\n"
                    for ec in entry['error_codes']:
                        md_content += f"| {ec.get('code', '')} | {ec.get('description', '')} | {ec.get('solution', '')} |\n"
                    md_content += "\n"
                
                md_content += "---\n\n"
            
            section_num += 1
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✅ 已导出Markdown到: {output_path}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        stats = {
            "total_entries": len(self.data["knowledge_base"]),
            "by_category": {},
            "by_priority": {1: 0, 2: 0, 3: 0}
        }
        
        for entry in self.data["knowledge_base"]:
            cat = entry.get("category", "其他")
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
            
            priority = entry.get("priority", 2)
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
        
        return stats
    
    def print_statistics(self) -> None:
        """打印知识库统计信息"""
        stats = self.get_statistics()
        
        print("\n" + "="*50)
        print("📊 知识库统计信息")
        print("="*50)
        print(f"总条目数: {stats['total_entries']}")
        print("\n按分类统计:")
        for cat, count in stats["by_category"].items():
            print(f"  - {cat}: {count}条")
        print("\n按优先级统计:")
        for priority, count in stats["by_priority"].items():
            print(f"  - 优先级{priority}: {count}条")
        print("="*50 + "\n")


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 初始化管理器
    kb = KnowledgeBaseManager()
    
    # 示例1: 添加知识条目
    print("\n📝 示例1: 添加知识条目")
    kb.add_entry(
        category="使用指导",
        subcategory="扫码指引",
        question="小鹏车辆应该在充电桩哪个位置扫码？",
        short_answer="充电桩顶部显示屏旁，绿色边框二维码",
        detailed_answer="请按以下步骤操作：\n1. 抬头查看充电桩顶部\n2. 找到绿色边框二维码\n3. 扫码后自动跳转小程序\n4. 选择充电模式开始",
        keywords=["扫码", "小鹏", "XPeng", "二维码"],
        tags=["扫码", "小鹏", "使用指导"],
        priority=1
    )
    
    # 示例2: 搜索知识条目
    print("\n🔍 示例2: 搜索知识条目")
    results = kb.search(query="特斯拉")
    print(f"找到 {len(results)} 条相关记录")
    for r in results:
        print(f"  - [{r['id']}] {r['question']}")
    
    # 示例3: 按分类搜索
    print("\n🔍 示例3: 按分类搜索")
    results = kb.search(category="故障处理")
    print(f"故障处理类共 {len(results)} 条")
    
    # 示例4: 打印统计信息
    kb.print_statistics()
    
    # 示例5: 导出为Markdown
    # kb.export_to_markdown()
