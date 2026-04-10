#!/usr/bin/env python3
"""
测试兜底流程确认同义词识别
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from graphs.nodes.fallback_node import _is_confirm

# 测试用例
test_cases = [
    # 用户要求的同义词
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
    ("收到", True),
    
    # 带标点的测试
    ("确认。", True),
    ("对！", True),
    ("好的，", True),
    ("行！", True),
    ("没问题～", True),
    ("OK！", True),
    
    # 原有关键词（验证不破坏现有功能）
    ("确认无误", True),
    ("对的", True),
    ("可以", True),
    ("嗯嗯", True),
    ("对了", True),
    ("正确", True),
    ("okay", True),
    
    # 否定测试（不应识别为确认）
    ("取消", False),
    ("不要了", False),
    ("不对", False),
    ("不行", False),
    ("有问题", False),
]

print("=" * 60)
print("🧪 兜底流程确认同义词识别测试")
print("=" * 60)
print()

passed = 0
failed = 0

for user_message, expected in test_cases:
    result = _is_confirm(user_message)
    status = "✅ 通过" if result == expected else "❌ 失败"
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    print(f"{status} - 输入: '{user_message}' -> 期望: {expected}, 实际: {result}")

print()
print("=" * 60)
print(f"📊 测试结果: 通过 {passed}/{len(test_cases)}, 失败 {failed}/{len(test_cases)}")
print("=" * 60)

if failed == 0:
    print()
    print("🎉 所有测试通过！修复成功！")
    sys.exit(0)
else:
    print()
    print("❌ 有测试失败！请检查修复！")
    sys.exit(1)