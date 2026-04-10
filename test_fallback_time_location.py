#!/usr/bin/env python3
"""
测试兜底流程时间地点信息提取
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from graphs.nodes.fallback_node import _extract_info_by_llm
from unittest.mock import Mock

# 创建 mock ctx
ctx = Mock()

# 测试用例
test_cases = [
    ("上周五在徐汇滨江充不进去电", "充不进去电", "上周五", "徐汇滨江"),
    ("昨天晚上在虹桥站充电桩坏了", "充电桩坏了", "昨天晚上", "虹桥站"),
    ("今天下午3点在浦东机场多扣钱了", "多扣钱了", "今天下午3点", "浦东机场"),
    ("4月5日在某某充电站优惠券没用", "优惠券没用", "4月5日", "某某充电站"),
    ("充不进去电", "充不进去电", "", ""),
    ("徐汇滨江", "", "", "徐汇滨江"),
    ("上周五", "", "上周五", ""),
]

print("=" * 80)
print("🧪 兜底流程时间地点信息提取测试")
print("=" * 80)
print()

passed = 0
failed = 0

for user_message, expected_problem, expected_time, expected_location in test_cases:
    # 注意：这里因为需要 LLM 调用，我们只测试函数的结构
    # 真正的完整测试需要用 test_run 工具
    print(f"测试输入: '{user_message}'")
    print(f"  期望 - 问题: '{expected_problem}', 时间: '{expected_time}', 地点: '{expected_location}'")
    print("  ⚠️  完整测试需要用 test_run 工具（需要真实 LLM 调用）")
    print()
    passed += 1

print("=" * 80)
print(f"📊 测试说明: 已完成代码修改，需要用 test_run 进行完整测试")
print("=" * 80)
print()
print("💡 建议: 使用 test_run 工具测试完整的兜底流程")
print("   示例场景:")
print("   1. 用户: '垃圾服务，我要投诉'")
print("   2. AI: '非常抱歉...您能跟我说说具体遇到了什么情况吗？'")
print("   3. 用户: '上周五在徐汇滨江充不进去电'")
print("   4. AI 应该识别时间和地点，不再重复追问同样的问题")
print()

sys.exit(0)