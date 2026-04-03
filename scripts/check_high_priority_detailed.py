#!/usr/bin/env python3
"""
仔细查看高优先级问题的回答内容，给出准确判断 - 详细版
"""
import pandas as pd

def main():
    input_file = '/workspace/projects/assets/知识库v1.2.xlsx'
    
    df = pd.read_excel(input_file)
    
    # 高优先级问题列表
    high_priority_list = [
        {'id': 'KB012', 'note': '押金没有退还怎么办？'},
        {'id': 'KB018', 'note': '如何申请充电发票？'},
        {'id': 'KB019', 'note': '如何查看我的充电账单？'},
        {'id': 'KB057', 'note': '对充电服务不满意如何投诉？'},
        {'id': 'KB059', 'note': '我想在停车场安装充电桩，需要怎么做？'},
        {'id': 'KB073', 'note': '充电已经完成了但我没有收到提醒怎么办？'},
        {'id': 'KB077', 'note': '小程序账单和微信/支付宝账单金额不一致，以哪个为准？'},
        {'id': 'KB079', 'note': '如何有效向运营商反馈充电问题？'},
        {'id': 'KB081', 'note': '小程序登录被锁定或账号异常怎么办？'},
        {'id': 'KB053', 'note': '发现充电桩故障如何报修？'},
        {'id': 'KB041', 'note': '充值的余额可以退款吗？'},
    ]
    
    results = []
    
    for item in high_priority_list:
        kb_id = item['id']
        row = df[df['ID'] == kb_id]
        
        if len(row) == 0:
            print(f"⚠️  未找到 ID: {kb_id}")
            continue
        
        row = row.iloc[0]
        
        question = str(row.get('问题', '')).strip()
        short_answer = str(row.get('简短回答', '')).strip()
        detailed_answer = str(row.get('详细回答', '')).strip()
        
        # 分析回答内容
        needs_fallback = False
        reason_type = ''
        
        # 检查1：回答中是否需要客服介入
        needs_customer_service = any(kw in short_answer or kw in detailed_answer 
                                      for kw in ['联系客服', '找客服', '拨打客服', '客服电话', '转人工', '人工处理', '专人处理'])
        
        # 检查2：回答中是否需要留下信息或进一步处理
        needs_followup = any(kw in short_answer or kw in detailed_answer 
                            for kw in ['留下', '请提供', '我们会', '尽快', '联系您', '帮您', '提交', '申请', '核实', '调查'])
        
        # 检查3：问题本身的类型
        is_funding_issue = any(kw in question for kw in ['退款', '押金', '发票', '账单', '投诉', '不满意', '争议', '多扣', '扣款', '核实', '不一致'])
        
        # 综合判断
        if is_funding_issue:
            needs_fallback = True
            reason_type = '涉及资金/账务/投诉类问题'
        elif needs_customer_service:
            needs_fallback = True
            reason_type = '需要客服介入'
        elif needs_followup:
            needs_fallback = True
            reason_type = '需要后续处理'
        else:
            needs_fallback = False
            reason_type = '只是操作指引'
        
        results.append({
            'id': kb_id,
            'question': question,
            'short_answer': short_answer,
            'detailed_answer': detailed_answer,
            'needs_fallback': needs_fallback,
            'reason_type': reason_type
        })
    
    # 输出详细分析
    print("="*150)
    print("🔍 知识库v1.2 - 高优先级问题详细分析报告")
    print("="*150)
    
    print(f"\n📊 总计检查: {len(results)} 个问题\n")
    
    # 分类输出
    fallback_items = [r for r in results if r['needs_fallback']]
    keep_items = [r for r in results if not r['needs_fallback']]
    
    print("="*150)
    print(f"🔴 【建议移除】 应该转到兜底流程的问题 ({len(fallback_items)} 个)")
    print("="*150)
    
    for item in fallback_items:
        print(f"\n📋 ID: {item['id']}")
        print(f"❓ 问题: {item['question']}")
        print(f"📝 简短回答: {item['short_answer']}")
        if len(item['detailed_answer']) > 200:
            print(f"📄 详细回答: {item['detailed_answer'][:200]}...")
        else:
            print(f"📄 详细回答: {item['detailed_answer']}")
        print(f"🎯 判断: 🔴 应该移除")
        print(f"📌 原因: {item['reason_type']}")
    
    print("\n" + "="*150)
    print(f"🟢 【建议保留】 可以作为知识性内容的问题 ({len(keep_items)} 个)")
    print("="*150)
    
    for item in keep_items:
        print(f"\n📋 ID: {item['id']}")
        print(f"❓ 问题: {item['question']}")
        print(f"📝 简短回答: {item['short_answer']}")
        print(f"🎯 判断: 🟢 建议保留")
        print(f"📌 原因: {item['reason_type']}")
    
    # 总结
    print("\n" + "="*150)
    print("📊 总结")
    print("="*150)
    print(f"\n🔴 建议移除: {len(fallback_items)} 个")
    print(f"🟢 建议保留: {len(keep_items)} 个")
    print(f"\n判断原则:")
    print("  1. 涉及退款、押金、发票、账单、投诉 → 🔴 应该移除")
    print("  2. 需要客服介入或后续处理 → 🔴 应该移除")
    print("  3. 只是操作指引，不需要客服 → 🟢 可以保留")
    
    print("\n" + "="*150)
    print("📋 建议移除的问题清单:")
    print("="*150)
    for item in fallback_items:
        print(f"- {item['id']}: {item['question']}")

if __name__ == '__main__':
    main()
