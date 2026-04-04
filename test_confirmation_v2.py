#!/usr/bin/env python3
"""
测试脚本 v2：测试确认判断逻辑优化
测试第一层否定词/继续补充词检测是否生效
"""

def test_confirmation_judgment():
    """测试确认判断逻辑"""
    print("=" * 80)
    print("测试确认判断逻辑优化（第二层保护）")
    print("=" * 80)
    
    # 否定词/继续补充词（第一层）
    deny_keywords = [
        "还没有", "还没", "没有", "不对", "错了", "等一下", "等等", 
        "我还要", "我想再", "我想补充", "我还要补充", "我想再说", 
        "我还想", "你说得不对", "你说的不对", "不是这样", "不是这个",
        "还不行", "还不够", "还没完", "还没好", "等会", "等会儿"
    ]
    
    # 确认词（第二层）
    confirm_keywords = [
        "确认", "确认无误", "没问题", "确认无误", "正确", "没错",
        "准确", "OK", "ok", "对的", "确认了", "确认呀", "没问题了",
        "没其他问题", "没其他问题了", "没有其他问题", "没有其他问题了",
        "就这样", "可以了", "好的没问题", "是对的", "确认正确"
    ]
    
    # 测试用例：用户消息 -> 预期结果（是否应该确认）
    test_cases = [
        # ========== 应该被第一层否定词拦截的 ==========
        ("还没有啊", False),
        ("我还要再补充点信息", False),
        ("你说得不对", False),
        ("不对啊", False),
        ("等一下，我再想想", False),
        ("还没，等下", False),
        ("你说的不对", False),
        ("不是这样的", False),
        ("不是这个问题", False),
        ("我还想补充一点", False),
        ("等等，我再补充点", False),
        ("还不行，我再想想", False),
        ("还没好，等下", False),
        ("等会儿，我再补充", False),
        
        # ========== 应该被第二层确认词接受的 ==========
        ("确认", True),
        ("确认无误", True),
        ("没问题", True),
        ("正确", True),
        ("没错", True),
        ("准确", True),
        ("对的", True),
        ("确认了", True),
        ("可以了", True),
        ("就这样", True),
        ("确认", True),
        ("确认无误", True),
        ("没问题了", True),
        ("没其他问题了", True),
        
        # ========== 混合情况：否定词优先 ==========
        ("确认？不对，等一下", False),
        ("对吗？不，你说得不对", False),
        ("没问题？等等，我再想想", False),
        ("没错，但我还想补充", False),
        ("准确，但等一下", False),
    ]
    
    print(f"\n测试用例数量: {len(test_cases)}")
    print(f"否定词数量: {len(deny_keywords)}")
    print(f"确认词数量: {len(confirm_keywords)}")
    print()
    
    passed = 0
    failed = 0
    
    for user_message, expected in test_cases:
        # 清理消息
        cleaned_message = user_message.strip()
        for char in "，。！？、；：""''！？.,;:!? ":
            cleaned_message = cleaned_message.replace(char, "")
        
        # 第一层判断：否定词检测
        is_deny = any(kw in user_message for kw in deny_keywords)
        
        # 第二层判断：确认词检测
        is_confirm = cleaned_message in confirm_keywords
        
        # 最终判断：只有没有被否定，并且被确认，才返回 True
        actual = (not is_deny) and is_confirm
        
        result = "✅ PASS" if actual == expected else "❌ FAIL"
        if actual == expected:
            passed += 1
        else:
            failed += 1
        
        status = "应该确认" if expected else "不应该确认"
        print(f"{result} | '{user_message}' -> {status} (否定检测: {is_deny}, 确认检测: {is_confirm})")
    
    print()
    print("=" * 80)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = test_confirmation_judgment()
    exit(0 if success else 1)
