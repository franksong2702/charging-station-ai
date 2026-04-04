#!/usr/bin/env python3
"""
测试脚本：验证基于 LLM 的意图识别
模拟测试各种用户消息的意图判断
"""

def test_llm_intent_classification():
    """
    模拟测试 LLM 意图分类逻辑
    注意：这里只是模拟，实际运行时需要调用真实的 LLM
    """
    print("=" * 80)
    print("基于 LLM 的意图识别测试")
    print("=" * 80)
    
    # 测试用例：(用户消息, 问题总结, 预期意图)
    test_cases = [
        # ========== 确认类 ==========
        ("确认", "用户遇到优惠券未抵扣问题", "confirm"),
        ("没问题", "用户遇到优惠券未抵扣问题", "confirm"),
        ("对的", "用户遇到充电故障", "confirm"),
        ("准确", "用户遇到计费错误", "confirm"),
        ("可以了", "用户遇到扣费问题", "confirm"),
        ("就这样", "用户遇到充电桩问题", "confirm"),
        ("确认无误", "用户遇到优惠券问题", "confirm"),
        
        # ========== 预告纠正类 ==========
        ("你说得不对", "用户遇到优惠券未抵扣问题", "announce_correction"),
        ("我还要补充", "用户遇到优惠券未抵扣问题", "announce_correction"),
        ("等一下", "用户遇到优惠券未抵扣问题", "announce_correction"),
        ("等等", "用户遇到充电故障", "announce_correction"),
        ("我还想再说", "用户遇到计费错误", "announce_correction"),
        ("你说的不对，我还要补充", "用户遇到扣费问题", "announce_correction"),
        ("等一下，我再想想", "用户遇到充电桩问题", "announce_correction"),
        
        # ========== 实际纠正类 ==========
        ("你说得不对，优惠券没有抵扣", "用户遇到优惠券未抵扣问题", "actual_correction"),
        ("不对，应该是充电失败了", "用户遇到充电故障", "actual_correction"),
        ("我的问题是优惠券过期了", "用户遇到优惠券问题", "actual_correction"),
        ("实际情况是计费有误", "用户遇到计费错误", "actual_correction"),
        ("错了，应该是扣费错误", "用户遇到扣费问题", "actual_correction"),
        ("你说得不对，充不进去电", "用户遇到充电问题", "actual_correction"),
        ("你说得不对，优惠券不能用", "用户遇到优惠券问题", "actual_correction"),
        
        # ========== 取消类 ==========
        ("算了不要了", "用户遇到问题", "cancel"),
        ("取消", "用户遇到问题", "cancel"),
        ("不用处理了", "用户遇到问题", "cancel"),
        
        # ========== 其他类 ==========
        ("你好", "用户遇到问题", "other"),
        ("谢谢", "用户遇到问题", "other"),
    ]
    
    print(f"\n测试用例数量: {len(test_cases)}")
    print()
    
    # 模拟 LLM 的判断逻辑（基于规则）
    def mock_llm_intent(user_message, problem_summary):
        """模拟 LLM 的意图判断"""
        # 取消关键词
        if any(kw in user_message for kw in ["算了", "取消", "不用处理"]):
            return "cancel", False, "检测到取消关键词"
        
        # 确认关键词
        confirm_keywords = ["确认", "没问题", "对的", "准确", "可以了", "就这样"]
        if any(kw == user_message.strip() or user_message.strip().startswith(kw) for kw in confirm_keywords):
            return "confirm", False, "检测到确认关键词"
        
        # 预告纠正关键词（没有给出具体问题描述）
        announce_keywords = ["你说得不对", "我还要补充", "等一下", "等等", "我还想"]
        has_problem_keywords = any(kw in user_message for kw in [
            "优惠券", "抵扣", "充电", "计费", "扣费", "故障", "失败", "错误"
        ])
        
        if any(kw in user_message for kw in announce_keywords) and not has_problem_keywords:
            return "announce_correction", False, "检测到预告纠正关键词"
        
        # 实际纠正（有具体问题描述）
        if has_problem_keywords:
            return "actual_correction", True, "包含具体问题描述"
        
        # 其他
        return "other", False, "无法归类为已知意图"
    
    passed = 0
    failed = 0
    
    for user_message, problem_summary, expected_intent in test_cases:
        # 模拟调用 LLM
        actual_intent, is_correction, reasoning = mock_llm_intent(user_message, problem_summary)
        
        # 验证结果
        is_correct = actual_intent == expected_intent
        result = "PASS" if is_correct else "FAIL"
        if is_correct:
            passed += 1
        else:
            failed += 1
        
        print(f"{result} | '{user_message:30s}' -> {actual_intent:20s} (预期: {expected_intent:20s})")
        print(f"       理由: {reasoning}")
        print()
    
    print("=" * 80)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 80)
    print()
    print("【注意】这是模拟测试，实际运行时需要调用真实的 LLM API")
    print("【优势】LLM 可以理解语义，不受限于固定关键词，能处理更多 corner case")
    
    return failed == 0


def show_llm_prompt():
    """显示 LLM 意图识别的提示词"""
    print("=" * 80)
    print("LLM 意图识别提示词设计")
    print("=" * 80)
    print()
    print("【提示词结构】")
    print("1. 角色定义：智能客服意图识别专家")
    print("2. 当前状态：用户看到的问题总结、用户回复")
    print("3. 任务说明：判断用户意图（确认/预告纠正/实际纠正/取消/其他）")
    print("4. 详细规则：每种意图的定义和示例")
    print("5. 输出格式：JSON格式，包含意图、是否纠正、判断理由")
    print()
    print("【优势】")
    print("1. 语义理解：不受限于固定关键词")
    print("2. 上下文感知：考虑对话历史")
    print("3. 灵活判断：处理各种 corner case")
    print("4. 可解释性：提供判断理由")
    print()


if __name__ == "__main__":
    success = test_llm_intent_classification()
    show_llm_prompt()
    exit(0 if success else 1)
