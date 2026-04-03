
#!/usr/bin/env python3
"""
充电桩智能客服数据分析报告生成器
功能：
1. 用户问得最多的问题统计
2. 兜底逻辑触发统计
3. 知识库缺失问题统计
"""
import sys
import os
import json
from datetime import datetime, timedelta
from collections import Counter

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def clean_question(text: str) -> str:
    """清理问题文本，用于统计"""
    if not text:
        return ""
    # 去掉标点符号、空格
    text = text.strip()
    # 简化处理：返回前50个字符作为问题标识
    return text[:50] if len(text) > 50 else text


def print_section(title: str):
    """打印分区标题"""
    print("\n" + "="*80)
    print(f"📊 {title}")
    print("="*80)


def generate_report():
    """生成完整的数据分析报告"""
    print("🚀 开始生成充电桩智能客服数据分析报告...")
    print(f"📅 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ==================== 1. 整体统计 ====================
    print_section("1. 整体数据统计")
    
    # 注意：这里我们通过SQL查询来获取数据
    # 实际项目中，你需要根据你的数据库连接方式来修改这部分
    
    print("💡 提示：本脚本提供SQL查询模板")
    print("请在数据库管理后台或使用 exec_sql 工具执行以下查询：")
    
    print("\n" + "-"*80)
    print("📊 【查询1】整体对话统计")
    print("-"*80)
    print("""
-- 查看总对话数
SELECT COUNT(*) as total_conversations
FROM conversation_history;

-- 按日期统计对话数
SELECT 
    DATE(created_at) as date,
    COUNT(*) as count
FROM conversation_history
GROUP BY DATE(created_at)
ORDER BY date DESC
LIMIT 14;
""")
    
    print("\n" + "-"*80)
    print("📊 【查询2】用户问得最多的问题 TOP 20")
    print("-"*80)
    print("""
-- 统计最常见的用户问题
SELECT 
    user_message,
    COUNT(*) as count
FROM conversation_history
GROUP BY user_message
ORDER BY count DESC
LIMIT 20;
""")
    
    print("\n" + "-"*80)
    print("📊 【查询3】兜底逻辑触发统计")
    print("-"*80)
    print("""
-- 查看所有兜底记录（fallback/complaint）
SELECT 
    id,
    user_message,
    reply_content,
    intent,
    created_at
FROM conversation_history
WHERE intent IN ('fallback', 'complaint')
ORDER BY created_at DESC
LIMIT 30;

-- 统计兜底触发次数（按日期）
SELECT 
    DATE(created_at) as date,
    COUNT(*) as fallback_count
FROM conversation_history
WHERE intent IN ('fallback', 'complaint')
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- 统计各类意图分布
SELECT 
    intent,
    COUNT(*) as count
FROM conversation_history
GROUP BY intent
ORDER BY count DESC;
""")
    
    print("\n" + "-"*80)
    print("📊 【查询4】工单记录统计")
    print("-"*80)
    print("""
-- 查看所有工单记录
SELECT 
    id,
    user_id,
    phone,
    license_plate,
    problem_summary,
    created_at
FROM case_records
ORDER BY created_at DESC
LIMIT 20;

-- 统计工单数量（按日期）
SELECT 
    DATE(created_at) as date,
    COUNT(*) as case_count
FROM case_records
GROUP BY DATE(created_at)
ORDER BY date DESC;
""")
    
    print("\n" + "-"*80)
    print("📊 【查询5】知识库缺失记录（最有价值！）")
    print("-"*80)
    print("""
-- 查看知识库缺失的问题（用于扩充知识库）
SELECT 
    id,
    user_message,
    reply_content,
    created_at
FROM dialog_records
WHERE record_type = '知识库缺失'
ORDER BY created_at DESC
LIMIT 30;

-- 统计知识库缺失记录数量（按日期）
SELECT 
    DATE(created_at) as date,
    COUNT(*) as missed_count
FROM dialog_records
WHERE record_type = '知识库缺失'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- 查看所有记录类型分布
SELECT 
    record_type,
    COUNT(*) as count
FROM dialog_records
GROUP BY record_type
ORDER BY count DESC;
""")
    
    print("\n" + "-"*80)
    print("📊 【查询6】评价反馈统计")
    print("-"*80)
    print("""
-- 查看评价反馈记录
SELECT 
    id,
    user_message,
    reply_content,
    feedback_type,
    created_at
FROM dialog_records
WHERE record_type = '评价反馈'
ORDER BY created_at DESC
LIMIT 20;

-- 统计好评/差评数量
SELECT 
    feedback_type,
    COUNT(*) as count
FROM dialog_records
WHERE record_type = '评价反馈'
GROUP BY feedback_type;
""")
    
    print("\n" + "="*80)
    print("🎯 使用说明")
    print("="*80)
    print("""
1. 复制上面的 SQL 查询语句
2. 在数据库管理后台或使用 exec_sql 工具执行
3. 根据查询结果分析和优化

📝 重点关注：
   - 【查询5】知识库缺失记录 - 这些问题可以加入知识库
   - 【查询2】常见问题 - 这些可以优化和补充
   - 【查询3】兜底记录 - 分析用户为什么会进入兜底流程
""")
    
    print("\n" + "="*80)
    print("✅ 报告模板生成完成！")
    print("="*80)


if __name__ == "__main__":
    generate_report()

