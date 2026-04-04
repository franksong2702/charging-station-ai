#!/usr/bin/env python3
"""
测试脚本 v3.3：测试改进后的确认判断逻辑
测试"预告性纠正"和"实际纠正"的区分
"""

def test_improved_confirmation_flow():
    """测试改进后的确认判断逻辑"""
    print("=" * 80)
    print("测试改进后的确认判断逻辑（区分预告性纠正和实际纠正）")
    print("=" * 80)
    
    # 否定词/继续补充词（第一层）
    deny_keywords = [
        "还没有", "还没", "没有", "不对", "错了", "等一下", "等等", 
        "我还要", "我想再", "我想补充", "我还要补充", "我想再说", 
        "我还想", "你说得不对", "你的不对", "不是这样", "不是这个",
        "还不行", "还不够", "还没完", "还没好", "等会", "等会儿"
    ]
    
    # 纯预告关键词
    pure_announcement_keywords = [
        "你说得不对", "你的不对", "等一下", "等等", "等会", "等会儿",
        "我还要补充", "我想再", "我还想", "我想补充", "我要补充"
    ]
    
    # 具体问题描述关键词（避免误匹配"你说得不对"）
    has_problem_keywords = [
        "优惠券", "抵扣", "计费", "扣费", "故障", 
        "失败", "错误", "情况是", "实际是", "应该", "充不进去",
        "充不上", "扫码", "会员", "退款"
    ]
    
    # 实际纠正关键词
    correction_keywords = [
        "不对", "错了", "不对嘛", "搞错了", "根本就不对", 
        "忽略", "漏掉", "没说", "没提到", "不是这个", 
        "我的问题是", "我的问题是", "情况是", "实际是"
    ]
    
    # 测试用例：用户消息 -> (应该更新总结?, 应该引导继续说?)
    test_cases = [
        # ========== 纯预告纠正（应该引导继续说） ==========
        ("你说得不对", (False, True)),
        ("你说的不对，我还要补充", (False, True)),
        ("等一下，我再想想", (False, True)),
        ("等等，我再补充点", (False, True)),
        ("我还要补充", (False, True)),
        ("我还想再说一点", (False, True)),
        ("等会儿", (False, True)),
        ("等等", (False, True)),
        ("我还想补充", (False, True)),
        ("等一下，我再想想怎么办", (False, True)),
        
        # ========== 实际纠正（包含具体问题描述，应该更新总结） ==========
        ("你说得不对，优惠券没有抵扣", (True, False)),
        ("你的不对，实际情况是充不进去电", (True, False)),
        ("我的问题是优惠券没有抵扣", (True, False)),
        ("不对，应该是充电桩坏了", (True, False)),
        ("错了，应该是计费有问题", (True, False)),
        ("实际情况是充电失败了", (True, False)),
        ("你的不对，扣费错误", (True, False)),
        ("你说得不对，充不进去电", (True, False)),
        ("你说的不对，优惠券不能用", (True, False)),
        ("你说的不对，应该扣50块", (True, False)),
        
        # ========== 纯确认（应该确认） ==========
        ("确认", (False, False)),
        ("没问题", (False, False)),
        ("对的", (False, False)),
        ("准确", (False, False)),
    ]
    
    print(f"\n测试用例数量: {len(test_cases)}")
    print()
    
    passed = 0
    failed = 0
    
    for user_message, (should_update_summary, should_guide_continue) in test_cases:
        # 【重要】按照代码的实际逻辑顺序进行判断
        
        # 第一步：否定词检测
        is_deny = any(kw in user_message for kw in deny_keywords)
        
        if is_deny:
            # 第二步：纯预告检测
            is_pure_announcement = (
                any(kw == user_message or user_message.strip().rstrip('.,，。') == kw for kw in pure_announcement_keywords) or
                (len(user_message) < 20 and any(kw in user_message for kw in pure_announcement_keywords))
            )
            
            # 第三步：检查是否包含具体问题描述关键词
            has_problem = any(kw in user_message for kw in has_problem_keywords)
            
            if is_pure_announcement and not has_problem:
                # 用户只是预告要纠正/补充，引导继续说
                will_update_summary = False
                will_guide_continue = True
            else:
                # 第四步：实际纠正检测
                is_correction = any(kw in user_message for kw in correction_keywords)
                
                if is_correction:
                    # 用户实际给出了纠正内容，更新总结
                    will_update_summary = True
                    will_guide_continue = False
                else:
                    # 用户补充内容，更新总结
                    will_update_summary = True
                    will_guide_continue = False
        else:
            # 没有检测到否定词（应该走确认逻辑）
            will_update_summary = False
            will_guide_continue = False
        
        # 验证结果
        update_correct = will_update_summary == should_update_summary
        guide_correct = will_guide_continue == should_guide_continue
        is_correct = update_correct and guide_correct
        
        result = "✅ PASS" if is_correct else "❌ FAIL"
        if is_correct:
            passed += 1
        else:
            failed += 1
        
        action = "引导继续说" if will_guide_continue else ("更新总结" if will_update_summary else "其他")
        expected = "引导继续说" if should_guide_continue else ("更新总结" if should_update_summary else "其他")
        
        print(f"{result} | '{user_message[:40]:40s}' -> {action:12s} (预期: {expected:12s})")
    
    print()
    print("=" * 80)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = test_improved_confirmation_flow()
    exit(0 if success else 1)
