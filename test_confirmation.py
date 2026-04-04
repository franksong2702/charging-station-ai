#!/usr/bin/env python3
"""
测试确认判断逻辑
验证用户说"还没有啊"、"我还要再补充点信息"、"你说得不对"时的行为
"""

def test_confirmation_logic():
    """测试确认判断逻辑"""
    print("=" * 60)
    print("测试确认判断逻辑")
    print("=" * 60)
    
    # 确认关键词
    confirm_keywords = [
        "确认", "确认无误", "没问题", "确认无误", "正确", "没错",
        "准确", "OK", "ok", "对的", "确认了", "确认呀", "没问题了",
        "没其他问题", "没其他问题了", "没有其他问题", "没有其他问题了",
        "就这样", "可以了", "好的没问题", "是对的", "确认正确"
    ]
    
    # 纠正关键词
    correction_keywords = [
        "不对", "错了", "不对嘛", "搞错了", "根本就不对", 
        "忽略", "漏掉", "没说", "没提到", "不是这个", "我的问题是"
    ]
    
    # 测试用例
    test_cases = [
        # (用户消息, 预期结果: 'confirm', 'correction', 'neither')
        ("确认", "confirm"),
        ("没问题", "confirm"),
        ("确认无误", "confirm"),
        ("可以了", "confirm"),
        ("你说得不对", "correction"),
        ("错了", "correction"),
        ("不对嘛", "correction"),
        ("搞错了", "correction"),
        ("还没有啊", "neither"),
        ("我还要再补充点信息", "neither"),
        ("我想再补充一点", "neither"),
        ("等一下，我还要说点", "neither"),
        ("好的，请收集我的信息", "neither"),
        ("可以开始收集", "neither"),
    ]
    
    print("\n测试结果：")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for user_message, expected in test_cases:
        # 清理消息
        cleaned_message = user_message.strip()
        for char in "，。！？、；：""''！？.,;:!? ":
            cleaned_message = cleaned_message.replace(char, "")
        
        # 判断
        is_confirm = cleaned_message in confirm_keywords
        is_correction = any(kw in user_message for kw in correction_keywords)
        
        if is_confirm:
            actual = "confirm"
        elif is_correction:
            actual = "correction"
        else:
            actual = "neither"
        
        status = "✓" if actual == expected else "✗"
        if actual == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} '{user_message}'")
        print(f"  清理后: '{cleaned_message}'")
        print(f"  预期: {expected}, 实际: {actual}")
        if actual != expected:
            print(f"  is_confirm: {is_confirm}, is_correction: {is_correction}")
        print()
    
    print("-" * 60)
    print(f"总计: {len(test_cases)} 个测试")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print("=" * 60)
    
    return failed == 0


def analyze_problem():
    """分析潜在问题"""
    print("\n" + "=" * 60)
    print("潜在问题分析")
    print("=" * 60)
    
    print("\n问题 1: 否定词/继续补充词检测缺失")
    print("-" * 60)
    print("当前代码只检测：")
    print("  - 确认词（精确匹配）")
    print("  - 纠正词（包含匹配）")
    print()
    print("缺失检测：")
    print("  - 否定词：'还没有', '不是', '不对', '等一下'")
    print("  - 继续补充词：'我还要再补充', '我想再说点', '等一下'")
    print()
    
    print("问题 2: 清理逻辑可能过度")
    print("-" * 60)
    print("当前清理逻辑会去掉所有标点和空格")
    print("这可能导致：")
    print("  - '好的没问题' → '好的没问题'（正确）")
    print("  - '好的，没问题' → '好的没问题'（正确）")
    print("  - 但可能影响其他判断")
    print()
    
    print("建议的修复方案：")
    print("-" * 60)
    print("1. 新增否定词/继续补充词检测")
    print("2. 在判断确认之前，先判断是否是否定/继续补充")
    print("3. 只有明确确认才发送邮件")
    print()


if __name__ == "__main__":
    success = test_confirmation_logic()
    analyze_problem()
    import sys
    sys.exit(0 if success else 1)
