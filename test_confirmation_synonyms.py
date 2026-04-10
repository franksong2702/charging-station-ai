#!/usr/bin/env python3
"""
测试兜底流程确认同义词识别
"""
import sys
import re

# 添加 src 目录到路径
sys.path.insert(0, '/workspace/projects/src')

def _is_confirm(user_message: str) -> bool:
    """判断用户是否在确认"""
    # 确认关键词（去掉标点后匹配）
    confirm_keywords = [
        "确认", "确认无误", "没问题", "是的", "对的", "好的", "行", "可以", "可以的", "嗯嗯",
        "准确", "没错", "对了", "正确", "就是这样", "同意", "好", "嗯", "要得",
        "对", "ok", "okay", "OK", "收到"
    ]
    msg = re.sub(r'[，。！？、\.\,\!\?\~\s]', '', user_message.lower())
    for kw in confirm_keywords:
        if kw in msg:
            return True
    return False

# 测试用例
test_cases = [
    # 要求的同义词
    ("确认", True),
    ("对", True),
    ("是的", True),
    ("好的", True),
    ("行", True),
    ("没问题", True),
    ("准确", True),
    ("没错", True),
    ("就是这样", True),
    ("可以的", True),
    ("同意", True),
    ("好", True),
    ("嗯", True),
    ("要得", True),
    ("OK", True),
    ("ok", True),
    
    # 带标点符号的
    ("确认。", True),
    ("对！", True),
    ("是的！", True),
    ("好的！", True),
    ("行！", True),
    ("没问题！", True),
    ("准确！", True),
    ("没错！", True),
    ("就是这样！", True),
    ("可以的！", True),
    ("同意！", True),
    ("好！", True),
    ("嗯！", True),
    ("要得！", True),
    ("OK！", True),
    ("ok！", True),
    
    # 带空格的
    (" 确认 ", True),
    (" 对 ", True),
    (" 是的 ", True),
    
    # 否定测试（不应该识别为确认）
    ("不确认", False),
    ("不对", False),
    ("不是的", False),
    ("不好的", False),
    ("不行", False),
    ("有问题", False),
    ("不准确", False),
    ("有错", False),
    ("不是这样", False),
    ("不可以", False),
    ("不同意", False),
    ("不好", False),
    ("不要得", False),
    
    # 混合情况
    ("好的，没问题", True),
    ("是的，确认", True),
    ("对，没错", True),
    ("行，可以的", True),
    ("嗯，好的", True),
]

print("=" * 80)
print("测试兜底流程确认同义词识别")
print("=" * 80)
print()

passed = 0
failed = 0

for user_input, expected in test_cases:
    result = _is_confirm(user_input)
    status = "✅ PASS" if result == expected else "❌ FAIL"
    if result == expected:
        passed += 1
    else:
        failed += 1
    print(f"{status} | 输入: '{user_input}' | 期望: {expected} | 实际: {result}")

print()
print("=" * 80)
print(f"测试结果: {passed} 通过, {failed} 失败")
print("=" * 80)

if failed == 0:
    print("\n🎉 所有测试通过！")
    sys.exit(0)
else:
    print(f"\n❌ {failed} 个测试失败")
    sys.exit(1)
