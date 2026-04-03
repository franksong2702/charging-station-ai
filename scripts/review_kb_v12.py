#!/usr/bin/env python3
"""
知识库v1.2审核脚本
"""
import pandas as pd
import os

def classify_question(question: str, answer: str) -> dict:
    """
    根据审核原则对问题进行分类
    """
    question = str(question).strip() if pd.notna(question) else ''
    answer = str(answer).strip() if pd.notna(answer) else ''
    
    if question == '' or question == 'nan':
        return {
            'category': '空行',
            'color': '⚪',
            'priority': '低',
            'action': '建议删除',
            'reasons': '空行或无效数据'
        }
    
    # 兜底性内容关键词
    fallback_keywords = [
        '投诉', '退款', '赔偿', '损失', '维权', '举报', '起诉',
        '不满意', '差评', '投诉电话', '人工客服', '转人工', '客服介入',
        '索赔', '投诉邮箱', '投诉渠道', '投诉部门', '监管', '投诉平台',
        '退款失败', '无法退款', '扣款', '多扣', '乱扣', '费用争议',
        '退费', '退款申请', '退款流程', '退款时间', '退款金额',
        '押金', '保证金', '押金退还', '保证金退还',
        '账单', '发票', '开票', '发票问题', '账单问题',
        '账号', '账户', '登录', '注册', '密码', '绑定', '解绑',
        '异常', '错误', '故障', '无法', '不能', '失败',
        '损坏', '坏了', '维修', '报修', '售后', '理赔',
        '联系客服', '客服处理', '客服解决', '专人处理',
        '申请', '提交', '处理', '解决', '跟进', '反馈',
        '查不到', '找不到', '无法查询', '无法获取',
        '安全', '隐私', '泄露', '被盗', '冒用',
        '法律', '律师', '诉讼', '仲裁', '调解',
        '协商', '沟通', '协调', '解决问题', '处理问题',
        '调查', '核实', '查证', '确认',
        '超时', '等待', '延误', '拖延',
        '不合理', '不公平', '不公正', '违规', '违法'
    ]
    
    # 知识性内容关键词（正向）
    knowledge_keywords = [
        '怎么用', '如何使用', '使用方法', '操作步骤', '教程', '指南',
        '在哪里', '位置', '地方', '地点', '怎么找', '怎么去',
        '多少钱', '价格', '费用', '收费', '计费', '怎么算',
        '需要什么', '要求', '条件', '准备', '材料',
        '注意事项', '安全', '提醒', '警告', '说明',
        '区别', '不同', '对比', '比较', '差异',
        '是什么', '介绍', '说明', '解释', '定义', '概念',
        '有哪些', '种类', '类型', '分类', '列表',
        '时间', '多久', '多长时间', '需要多久',
        '可以吗', '能否', '是否', '能不能',
        '为什么', '原因', '因为', '由于',
        '怎么办', '怎么处理', '怎么解决', '方法', '办法',
        '步骤', '流程', '过程', '程序',
        '功能', '作用', '用途', '特点', '特性',
        '优势', '缺点', '好处', '坏处',
        '品牌', '型号', '规格', '参数',
        '安装', '设置', '配置', '调试',
        '充电', '使用', '扫码', '启动', '停止',
        '会员', '优惠', '活动', '折扣',
        '天气', '雨天', '雪天', '高温', '低温',
        '车内', '有人', '没人',
        '锁枪', '解锁', '拔枪', '插枪',
        '指示灯', '显示', '屏幕', '黑屏',
        '功率', '速度', '快慢', '时间',
        '占位', '超时', '费用', '罚款',
        '小程序', 'App', '软件', '应用',
        '华为', '特斯拉', '蔚来', '比亚迪', '特来电',
        '星星充电', '国家电网', '小桔充电', '云快充',
        '换电', '换电站', '换电方法',
        '急停', '安全检查', 'V2G', '即插即充'
    ]
    
    is_fallback = False
    is_knowledge = False
    reasons = []
    
    # 检查兜底关键词
    for keyword in fallback_keywords:
        if keyword in question or keyword in answer:
            is_fallback = True
            reasons.append(f"包含兜底关键词: '{keyword}'")
            break
    
    # 检查知识性关键词
    for keyword in knowledge_keywords:
        if keyword in question:
            is_knowledge = True
            reasons.append(f"包含知识关键词: '{keyword}'")
            break
    
    # 特殊规则判断
    # 1. 如果问题明确需要客服介入 = 兜底
    if any(kw in question for kw in ['转人工', '联系客服', '人工客服', '投诉', '赔偿']):
        is_fallback = True
        if "明确需要客服介入" not in reasons:
            reasons.append("明确需要客服介入")
    
    # 2. 如果问题是关于操作指引、位置、价格 = 知识性
    if any(kw in question for kw in ['怎么用', '在哪里', '多少钱', '步骤', '流程']):
        is_knowledge = True
        if "属于操作指引/信息查询类" not in reasons:
            reasons.append("属于操作指引/信息查询类")
    
    # 3. 退款/押金/账单 = 兜底（需要人工处理）
    if any(kw in question for kw in ['退款', '押金', '账单', '发票', '多扣', '扣款']):
        is_fallback = True
        if "涉及资金/账务问题，需要人工处理" not in reasons:
            reasons.append("涉及资金/账务问题，需要人工处理")
    
    # 最终分类
    if is_fallback and not is_knowledge:
        category = '兜底性内容（不应该放在知识库中)'
        color = '🔴'
        priority = '高'
        action = '建议移除'
    elif is_knowledge and not is_fallback:
        category = '知识性内容（应该保留)'
        color = '🟢'
        priority = '低'
        action = '建议保留'
    elif is_fallback and is_knowledge:
        # 两者都有，需要人工判断
        category = '需要人工判断'
        color = '🟡'
        priority = '中'
        action = '需要人工审核'
    else:
        category = '需要人工判断'
        color = '🟡'
        priority = '中'
        action = '需要人工审核'
    
    return {
        'category': category,
        'color': color,
        'priority': priority,
        'action': action,
        'reasons': '; '.join(reasons) if reasons else ''
    }

def main():
    """主函数"""
    input_file = '/workspace/projects/assets/知识库v1.2.xlsx'
    output_file = '/workspace/projects/assets/知识库v1.2_带审核结果.xlsx'
    
    if not os.path.exists(input_file):
        print(f"❌ 文件不存在: {input_file}")
        return
    
    # 读取文件
    print(f"📖 读取文件: {input_file}")
    df = pd.read_excel(input_file)
    print(f"✅ 成功读取 {len(df)} 条记录")
    print(f"📋 列名: {list(df.columns)}")
    
    # 添加审核结果列
    print("🔍 开始审核...")
    
    audit_categories = []
    audit_colors = []
    audit_priorities = []
    audit_actions = []
    audit_reasons = []
    
    for idx, row in df.iterrows():
        question = row.get('问题', '')
        answer = row.get('简短回答', '') or row.get('详细回答', '')
        
        result = classify_question(question, answer)
        
        audit_categories.append(result['category'])
        audit_colors.append(result['color'])
        audit_priorities.append(result['priority'])
        audit_actions.append(result['action'])
        audit_reasons.append(result['reasons'])
        
        if (idx + 1) % 20 == 0:
            print(f"   已处理 {idx + 1}/{len(df)} 条...")
    
    # 添加列到DataFrame
    df['审核标识'] = audit_colors
    df['审核分类'] = audit_categories
    df['优先级'] = audit_priorities
    df['处理建议'] = audit_actions
    df['审核原因'] = audit_reasons
    
    # 重新排列列的顺序，把审核列放在前面
    cols = list(df.columns)
    audit_cols = ['审核标识', '审核分类', '优先级', '处理建议', '审核原因']
    other_cols = [col for col in cols if col not in audit_cols]
    new_order = audit_cols + other_cols
    df = df[new_order]
    
    # 保存文件
    print(f"💾 保存文件: {output_file}")
    df.to_excel(output_file, index=False)
    print(f"✅ 文件已保存: {output_file}")
    
    # 统计结果
    fallback_count = sum(1 for c in audit_categories if '兜底' in c)
    knowledge_count = sum(1 for c in audit_categories if '知识性' in c)
    manual_count = sum(1 for c in audit_categories if '需要人工' in c)
    empty_count = sum(1 for c in audit_categories if '空行' in c)
    
    print("\n" + "="*80)
    print("📊 知识库v1.2 审核统计结果:")
    print("="*80)
    print(f"🟢 知识性内容（应该保留）: {knowledge_count} 条")
    print(f"🔴 兜底性内容（不应该放在知识库中): {fallback_count} 条")
    print(f"🟡 需要人工判断: {manual_count} 条")
    print(f"⚪ 空行/无效数据: {empty_count} 条")
    print(f"📋 总计: {len(df)} 条")
    print("="*80)
    
    # 显示部分示例
    print("\n🔴 兜底性内容（不应该放在知识库中）:")
    fallback_df = df[df['审核分类'].str.contains('兜底', na=False)]
    if len(fallback_df) > 0:
        for idx, row in fallback_df.iterrows():
            print(f"\n{row['审核标识']} ID: {row.get('ID', 'N/A')}")
            print(f"   问题: {row['问题']}")
            print(f"   建议: {row['处理建议']}")
            print(f"   原因: {row['审核原因']}")
    else:
        print("   ✅ 未发现明显的兜底性内容！")
    
    print("\n" + "="*80)
    print("🟡 需要人工判断的内容（前10条）:")
    print("="*80)
    manual_df = df[df['审核分类'].str.contains('需要人工', na=False)]
    for idx, row in manual_df.head(10).iterrows():
        print(f"\n{row['审核标识']} ID: {row.get('ID', 'N/A')}")
        print(f"   问题: {row['问题']}")
        print(f"   建议: {row['处理建议']}")
        print(f"   原因: {row['审核原因']}")
    
    print("\n" + "="*80)
    print("🟢 知识性内容示例（前5条）:")
    print("="*80)
    knowledge_df = df[df['审核分类'].str.contains('知识性', na=False)]
    for idx, row in knowledge_df.head(5).iterrows():
        print(f"\n{row['审核标识']} ID: {row.get('ID', 'N/A')}")
        print(f"   问题: {row['问题']}")
        print(f"   建议: {row['处理建议']}")

if __name__ == '__main__':
    main()
