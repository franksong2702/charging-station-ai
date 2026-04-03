
#!/usr/bin/env python3
"""
分析真实用户问题，过滤测试数据
"""
# 测试数据关键词（用于过滤）
TEST_DATA_PATTERNS = [
    "手机", "车牌", "手机号", "车牌号",  # 测试手机号/车牌
    "13812345678", "13800138000", "15300635189",  # 测试手机号
    "京A12345", "京A88888", "沪ADG 9676",  # 测试车牌
    "确认", "算了", "好的，谢谢",  # 测试交互
    "我要投诉", "垃圾服务", "垃圾系统",  # 测试投诉
    "今天天气",  # 测试闲聊
    "转人工",  # 这个可能是真实的，但也可能是测试
]

def is_test_data(message):
    """判断是否是测试数据"""
    if not message:
        return True
    
    message_lower = message.lower()
    
    # 检查是否包含测试关键词
    for pattern in TEST_DATA_PATTERNS:
        if pattern in message:
            return True
    
    # 检查是否是纯数字或太短
    if len(message.strip()) < 4:
        return True
    
    return False

# 从之前的查询结果中过滤
all_questions = [
    ("充电桩怎么用", 44),
    ("如何成为会员享受优惠？", 16),
    ("你好", 14),
    ("充电桩怎么用？", 13),
    ("充电枪拔不出来怎么办", 12),
    ("特斯拉怎么充电", 10),
    ("怎么充电", 10),
    ("转人工", 8),
    ("手机13812345678，车牌京A12345", 8),
    ("特斯拉的车怎么充电", 8),
    ("比亚迪的车怎么充电", 7),
    ("充电枪拔不出来", 7),
    ("确认", 6),
    ("特斯拉充电桩怎么扫码？", 6),
    ("充不进去电怎么办", 6),
    ("算了，不用了", 5),
    ("直流快充和交流慢充有什么区别？", 5),
    ("充电的费用是怎么算的？", 5),
    ("手机号,15300635189，车牌号，沪ADG 9676", 5),
    ("我要投诉", 5),
    ("好的，谢谢！", 5),
    ("请问特斯拉的车辆怎么充电", 4),
    ("垃圾服务，我要投诉", 4),
    ("特斯拉怎么充电？", 4),
    ("请问特斯拉怎么充电", 4),
    ("今天天气怎么样？", 3),
    ("不正确，我的诉求是收了我占位费，但是没有提示我。我该如何索赔？", 3),
    ("垃圾系统，转人工", 3),
    ("充电桩怎么使用", 3),
    ("手机13800138000，车牌京A88888", 3),
]

print("="*80)
print("📊 过滤测试数据后的真实用户问题 TOP 20")
print("="*80)

# 过滤并合并相似问题
real_questions = {}
for question, count in all_questions:
    if is_test_data(question):
        continue
    
    # 合并相似问题
    question_clean = question.replace("？", "?").strip()
    
    # 合并"充电桩怎么用"和"充电桩怎么用？"
    if "充电桩怎么用" in question_clean:
        key = "充电桩怎么用"
    elif "特斯拉怎么充电" in question_clean:
        key = "特斯拉怎么充电"
    elif "充电枪拔不出来" in question_clean:
        key = "充电枪拔不出来怎么办"
    else:
        key = question_clean
    
    if key in real_questions:
        real_questions[key] += count
    else:
        real_questions[key] = count

# 排序并显示
sorted_questions = sorted(real_questions.items(), key=lambda x: x[1], reverse=True)

print(f"\n🎯 过滤后，共 {len(sorted_questions)} 个真实问题\n")
print("-"*80)
print(f"{'排名':<6}{'问题':<40}{'次数':>8}")
print("-"*80)

for i, (question, count) in enumerate(sorted_questions[:20], 1):
    print(f"{i:<6}{question:<40}{count:>8}")

print("-"*80)
print("\n💡 说明：")
print("  - 已过滤测试数据（手机号、车牌、确认、投诉等）")
print("  - 已合并相似问题（如'充电桩怎么用'和'充电桩怎么用？'）")

