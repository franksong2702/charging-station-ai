#!/usr/bin/env python3
"""
仔细查看高优先级问题的回答内容，给出准确判断
"""
import pandas as pd

def main():
    input_file = '/workspace/projects/assets/知识库v1.2.xlsx'
    
    df = pd.read_excel(input_file)
    
    print("="*120)
    print("🔍 知识库v1.2 - 高优先级问题详细检查")
    print("="*120)
    
    # 高优先级问题列表
    high_priority_ids = [
        'KB012',  # 押金没有退还怎么办？
        'KB018',  # 如何申请充电发票？
        'KB019',  # 如何查看我的充电账单？
        'KB057',  # 对充电服务不满意如何投诉？
        'KB059',  # 充了10度电但扣了很多钱，对不上怎么回事？
        'KB073',  # 我觉得充电桩多计了电量，怎么核实？
        'KB077',  # 小程序账单和微信/支付宝账单金额不一致，以哪个为准？
        'KB079',  # 如何有效向运营商反馈充电问题？
        'KB081',  # 小程序登录被锁定或账号异常怎么办？
        'KB053',  # 发现充电桩故障如何报修？
        'KB041',  # 充值的余额可以退款吗？（已识别的兜底内容）
    ]
    
    for kb_id in high_priority_ids:
        # 查找对应记录
        row = df[df['ID'] == kb_id]
        
        if len(row) == 0:
            print(f"\n⚠️  未找到 ID: {kb_id}")
            continue
        
        row = row.iloc[0]
        
        question = str(row.get('问题', '')).strip()
        short_answer = str(row.get('简短回答', '')).strip()
        detailed_answer = str(row.get('详细回答', '')).strip()
        category = str(row.get('分类', '')).strip()
        subcategory = str(row.get('子分类', '')).strip()
        
        print(f"\n{'='*120}")
        print(f"📋 ID: {kb_id}")
        print(f"🏷️  分类: {category} / {subcategory}")
        print(f"❓ 问题: {question}")
        print(f"\n📝 简短回答:")
        print(f"   {short_answer}")
        print(f"\n📄 详细回答:")
        if len(detailed_answer) > 500:
            print(f"   {detailed_answer[:500]}...")
        else:
            print(f"   {detailed_answer}")
        
        # 判断逻辑
        needs_fallback = False
        reasons = []
        
        # 检查回答中是否包含需要客服介入的关键词
        fallback_keywords_in_answer = [
            '联系客服', '客服处理', '找客服', '拨打客服', '客服电话',
            '转人工', '人工处理', '专人处理',
            '投诉', '反馈', '提交', '申请', '核实', '调查',
            '留下', '请提供', '我们会', '尽快', '联系您', '帮您',
            '拨打', '电话', '热线', '客服',
            '记录', '反馈', '提交工单', '工单',
            '退款', '押金', '发票', '账单', '争议', '投诉'
        ]
        
        for keyword in fallback_keywords_in_answer:
            if keyword in short_answer or keyword in detailed_answer:
                needs_fallback = True
                if f"回答中包含 '{keyword}'" not in reasons:
                    reasons.append(f"回答中包含 '{keyword}'")
        
        # 检查问题本身的类型
        question_lower = question.lower()
        
        if any(kw in question_lower for kw in ['退款', '押金', '发票', '账单', '投诉', '不满意', '争议', '多扣', '扣款', '核实', '不一致']):
            needs_fallback = True
            if "问题本身涉及资金/账务/投诉" not in reasons:
                reasons.append("问题本身涉及资金/账务/投诉")
        
        # 给出最终判断
        print(f"\n{'='*120}")
        if needs_fallback:
            print(f"🔴 【建议移除】 应该转到兜底流程")
            print(f"   原因: {'; '.join(reasons)}")
        else:
            print(f"🟢 【建议保留】 可以作为知识性内容")
            print(f"   原因: 回答只是指引，不需要客服介入")
        
        print("="*120)
    
    # 总结
    print("\n" + "="*120)
    print("📊 检查总结")
    print("="*120)
    print("\n提示：请根据每个问题的实际回答内容来判断：")
    print("  - 如果回答只是给出操作指引（如'在小程序中点击XX'）→ 可以保留")
    print("  - 如果回答需要客服介入（如'联系客服处理'、'留下联系方式'）→ 应该移除")
    print("  - 如果问题本身涉及退款、押金、发票、账单、投诉 → 应该移除")

if __name__ == '__main__':
    main()
