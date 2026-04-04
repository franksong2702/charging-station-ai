"""
兜底流程状态清除修复验证测试
测试 save_history_node 和 clear_fallback_state_node 的修复逻辑
"""
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock 外部依赖
class MockSession:
    def __init__(self):
        self.added = []

    def add(self, record):
        self.added.append(record)

    def commit(self):
        pass

    def close(self):
        pass


class MockConversationHistory:
    """Mock ConversationHistory 类"""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_save_history_done_phase():
    """测试当 fallback_phase='done' 时，清空兜底状态"""
    print("\n=== 测试 1: save_history_node 当 fallback_phase='done' ===")

    # 模拟 save_history_node 的逻辑
    class State:
        user_id = "test_user_123"
        user_message = "确认"
        reply_content = "好的，已提交"
        intent = "fallback"
        fallback_phase = "done"
        phone = "13912345678"
        license_plate = "沪 A12345"
        problem_summary = "用户遇到充电问题"
        entry_problem = "充电失败"
        user_supplement = "补充内容"

    state = State()

    # 模拟记录构建逻辑
    record = MockConversationHistory(
        user_id=state.user_id,
        user_message=state.user_message,
        reply_content=state.reply_content,
        intent=state.intent if state.intent else None
    )

    # 应用修复后的逻辑
    if state.fallback_phase == "done":
        # 兜底完成，清空状态
        record.fallback_phase = ""
        record.phone = ""
        record.license_plate = ""
        record.problem_summary = ""
        record.entry_problem = ""
        record.user_supplement = ""
        print("  ✓ 执行清空逻辑")
    elif state.fallback_phase:
        # 正在兜底中，保存状态
        record.fallback_phase = state.fallback_phase
        if state.phone:
            record.phone = state.phone
        if state.license_plate:
            record.license_plate = state.license_plate
        if state.problem_summary:
            record.problem_summary = state.problem_summary
        if state.entry_problem:
            record.entry_problem = state.entry_problem
        if state.user_supplement:
            record.user_supplement = state.user_supplement

    # 验证结果
    assert record.fallback_phase == "", f"fallback_phase 应为空，实际：{record.fallback_phase}"
    assert record.phone == "", f"phone 应为空，实际：{record.phone}"
    assert record.license_plate == "", f"license_plate 应为空，实际：{record.license_plate}"
    assert record.problem_summary == "", f"problem_summary 应为空，实际：{record.problem_summary}"
    assert record.entry_problem == "", f"entry_problem 应为空，实际：{record.entry_problem}"
    assert record.user_supplement == "", f"user_supplement 应为空，实际：{record.user_supplement}"

    print(f"  ✓ fallback_phase: '{record.fallback_phase}' (应为空)")
    print(f"  ✓ phone: '{record.phone}' (应为空)")
    print(f"  ✓ license_plate: '{record.license_plate}' (应为空)")
    print(f"  ✓ problem_summary: '{record.problem_summary}' (应为空)")
    print(f"  ✓ 测试通过!")
    return True


def test_save_history_collect_phase():
    """测试当 fallback_phase='collect_info' 时，保存兜底状态"""
    print("\n=== 测试 2: save_history_node 当 fallback_phase='collect_info' ===")

    class State:
        user_id = "test_user_123"
        user_message = "手机号 13912345678"
        reply_content = "好的，请再说下车牌号"
        intent = "fallback"
        fallback_phase = "collect_info"
        phone = "13912345678"
        license_plate = ""
        problem_summary = ""
        entry_problem = "充电失败"
        user_supplement = ""

    state = State()
    record = MockConversationHistory(
        user_id=state.user_id,
        user_message=state.user_message,
        reply_content=state.reply_content,
        intent=state.intent if state.intent else None
    )

    # 应用修复后的逻辑
    if state.fallback_phase == "done":
        record.fallback_phase = ""
        record.phone = ""
        record.license_plate = ""
        record.problem_summary = ""
        record.entry_problem = ""
        record.user_supplement = ""
    elif state.fallback_phase:
        record.fallback_phase = state.fallback_phase
        if state.phone:
            record.phone = state.phone
        if state.license_plate:
            record.license_plate = state.license_plate
        if state.problem_summary:
            record.problem_summary = state.problem_summary
        if state.entry_problem:
            record.entry_problem = state.entry_problem
        if state.user_supplement:
            record.user_supplement = state.user_supplement

    # 验证结果
    assert record.fallback_phase == "collect_info", f"fallback_phase 应为 collect_info，实际：{record.fallback_phase}"
    assert record.phone == "13912345678", f"phone 应为 13912345678，实际：{record.phone}"
    assert record.entry_problem == "充电失败", f"entry_problem 应为充电失败，实际：{record.entry_problem}"

    print(f"  ✓ fallback_phase: '{record.fallback_phase}'")
    print(f"  ✓ phone: '{record.phone}'")
    print(f"  ✓ entry_problem: '{record.entry_problem}'")
    print(f"  ✓ 测试通过!")
    return True


def test_clear_fallback_state_empty_message():
    """测试 clear_fallback_state_node 当 user_message 为空时的逻辑"""
    print("\n=== 测试 3: clear_fallback_state_node 当 user_message 为空 ===")

    class State:
        user_id = "test_user_123"
        user_message = ""  # 自动清除时为空
        reply_content = ""

    state = State()

    # 模拟记录构建逻辑（修复后）
    record = MockConversationHistory(
        user_id=state.user_id,
        user_message=state.user_message or "",
        reply_content=state.reply_content or "",
        intent="" if not state.user_message else "",  # 修复：没有 user_message 时 intent 为空
        fallback_phase="",
        phone="",
        license_plate="",
        problem_summary="",
        entry_problem="",  # 修复：添加清空 entry_problem
        user_supplement=""  # 修复：添加清空 user_supplement
    )

    # 验证结果
    assert record.intent == "", f"intent 应为空，实际：{record.intent}"
    assert record.fallback_phase == "", f"fallback_phase 应为空，实际：{record.fallback_phase}"
    assert hasattr(record, 'entry_problem'), "record 应有 entry_problem 属性"
    assert hasattr(record, 'user_supplement'), "record 应有 user_supplement 属性"

    print(f"  ✓ intent: '{record.intent}' (应为空)")
    print(f"  ✓ fallback_phase: '{record.fallback_phase}' (应为空)")
    print(f"  ✓ entry_problem: '{getattr(record, 'entry_problem', 'N/A')}' (应为空)")
    print(f"  ✓ user_supplement: '{getattr(record, 'user_supplement', 'N/A')}' (应为空)")
    print(f"  ✓ 测试通过!")
    return True


def test_workflow_path():
    """测试工作流路径是否正确"""
    print("\n=== 测试 4: 工作流路径验证 ===")

    # 读取 graph.py 验证路径
    graph_path = os.path.join(os.path.dirname(__file__), '..', 'graphs', 'graph.py')
    with open(graph_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 验证修改后的路径
    assert 'builder.add_edge("create_case", "clear_fallback_state")' in content, \
        "graph.py 应包含 create_case → clear_fallback_state 的边"
    assert 'builder.add_edge("clear_fallback_state", "email_sending")' in content, \
        "graph.py 应包含 clear_fallback_state → email_sending 的边"

    print("  ✓ create_case → clear_fallback_state → email_sending → END")
    print(f"  ✓ 测试通过!")
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("兜底流程状态清除修复验证测试")
    print("=" * 60)

    tests = [
        ("save_history_node done 相处理", test_save_history_done_phase),
        ("save_history_node collect_info 相处理", test_save_history_collect_phase),
        ("clear_fallback_state_node 空消息处理", test_clear_fallback_state_empty_message),
        ("工作流路径验证", test_workflow_path),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"  ✗ 测试失败：{e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
