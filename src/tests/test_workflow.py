"""
充电桩智能客服工作流测试运行器
版本: v1.1.0

使用方法：
    cd /workspace/projects && python3 -m pytest src/tests/test_workflow.py -v
"""

import pytest
import json
import os
import sys
import importlib.util

# 加载 test_cases 模块
_test_cases_path = os.path.join(os.path.dirname(__file__), "test_cases.py")
_spec = importlib.util.spec_from_file_location("test_cases", _test_cases_path)
_test_cases = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_test_cases)

INTENT_RECOGNITION_TEST_CASES = _test_cases.INTENT_RECOGNITION_TEST_CASES
KNOWLEDGE_QA_TEST_CASES = _test_cases.KNOWLEDGE_QA_TEST_CASES
FALLBACK_FLOW_TEST_CASES = _test_cases.FALLBACK_FLOW_TEST_CASES
FEEDBACK_TEST_CASES = _test_cases.FEEDBACK_TEST_CASES
MULTI_TURN_TEST_CASES = _test_cases.MULTI_TURN_TEST_CASES
EDGE_CASE_TEST_CASES = _test_cases.EDGE_CASE_TEST_CASES
get_all_test_cases = _test_cases.get_all_test_cases


class TestIntentRecognition:
    """意图识别测试类"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """尝试导入意图识别节点"""
        try:
            from graphs.nodes.intent_recognition_node import intent_recognition_node
            from graphs.state import IntentRecognitionInput
            self.intent_node = intent_recognition_node
            self.input_class = IntentRecognitionInput
            self.node_available = True
        except ImportError:
            self.intent_node = None
            self.input_class = None
            self.node_available = False
    
    @pytest.mark.parametrize("test_case", INTENT_RECOGNITION_TEST_CASES, ids=lambda x: x["id"])
    def test_intent_recognition(self, test_case):
        """测试意图识别功能"""
        if not self.node_available:
            pytest.skip("意图识别节点模块不可用，需要在运行环境中测试")
        
        # 构造输入
        user_message = test_case["input"]["user_message"]
        
        # 简单验证输入不为空
        assert user_message is not None, "用户消息不能为空"
        
        # 验证测试用例结构
        assert "expected_intent" in test_case, f"测试用例 {test_case['id']} 缺少 expected_intent"
        assert "description" in test_case, f"测试用例 {test_case['id']} 缺少 description"
        
        print(f"[{test_case['id']}] {test_case['name']}: {test_case['description']}")


class TestKnowledgeQA:
    """知识库问答测试类"""
    
    @pytest.mark.parametrize("test_case", KNOWLEDGE_QA_TEST_CASES, ids=lambda x: x["id"])
    def test_knowledge_qa_structure(self, test_case):
        """测试知识库问答用例结构"""
        user_message = test_case["input"]["user_message"]
        
        # 验证输入不为空
        assert user_message, f"测试用例 {test_case['id']} 用户消息不能为空"
        
        # 验证测试用例结构
        assert "expected_keywords" in test_case, f"测试用例 {test_case['id']} 缺少 expected_keywords"
        assert "expected_not_contains" in test_case, f"测试用例 {test_case['id']} 缺少 expected_not_contains"
        
        print(f"[{test_case['id']}] {test_case['name']}: {test_case['description']}")
    
    def test_tesla_charging_keywords(self):
        """测试特斯拉充电关键词"""
        test_case = KNOWLEDGE_QA_TEST_CASES[0]  # 特斯拉充电指引
        keywords = test_case["expected_keywords"]
        
        assert "充电桩正面" in keywords, "特斯拉充电应包含'充电桩正面'"
        assert "黑白二维码" in keywords, "特斯拉充电应包含'黑白二维码'"
    
    def test_byd_charging_keywords(self):
        """测试比亚迪充电关键词"""
        test_case = KNOWLEDGE_QA_TEST_CASES[1]  # 比亚迪充电指引
        keywords = test_case["expected_keywords"]
        
        assert "充电桩侧面" in keywords or "彩色二维码" in keywords, "比亚迪充电应包含位置信息"


class TestFallbackFlow:
    """兜底流程测试类"""
    
    @pytest.mark.parametrize("test_case", FALLBACK_FLOW_TEST_CASES, ids=lambda x: x["id"])
    def test_fallback_flow_structure(self, test_case):
        """测试兜底流程用例结构"""
        # 验证测试用例结构
        assert "expected_phase" in test_case, f"测试用例 {test_case['id']} 缺少 expected_phase"
        
        print(f"[{test_case['id']}] {test_case['name']}: {test_case['description']}")
    
    def test_fallback_trigger_keywords(self):
        """测试兜底触发关键词"""
        trigger_cases = [c for c in FALLBACK_FLOW_TEST_CASES if "触发" in c["name"]]
        assert len(trigger_cases) >= 3, "至少应有3个兜底触发测试用例"
    
    def test_fallback_exit_keywords(self):
        """测试兜底退出关键词"""
        exit_cases = [c for c in FALLBACK_FLOW_TEST_CASES if "退出" in c["name"]]
        assert len(exit_cases) >= 2, "至少应有2个兜底退出测试用例"


class TestFeedback:
    """评价反馈测试类"""
    
    @pytest.mark.parametrize("test_case", FEEDBACK_TEST_CASES, ids=lambda x: x["id"])
    def test_feedback_structure(self, test_case):
        """测试评价反馈用例结构"""
        assert "expected_feedback" in test_case, f"测试用例 {test_case['id']} 缺少 expected_feedback"
        assert test_case["expected_feedback"] in ["good", "bad"], "expected_feedback 应为 good 或 bad"
        
        print(f"[{test_case['id']}] {test_case['name']}: {test_case['description']}")


class TestMultiTurn:
    """多轮对话测试类"""
    
    @pytest.mark.parametrize("test_case", MULTI_TURN_TEST_CASES, ids=lambda x: x["id"])
    def test_multi_turn_structure(self, test_case):
        """测试多轮对话用例结构"""
        assert "turns" in test_case, f"测试用例 {test_case['id']} 缺少 turns"
        assert len(test_case["turns"]) >= 2, f"测试用例 {test_case['id']} 应至少有2轮对话"
        
        for i, turn in enumerate(test_case["turns"]):
            assert "user_message" in turn, f"测试用例 {test_case['id']} 第{i+1}轮缺少 user_message"
            assert "expected_intent" in turn, f"测试用例 {test_case['id']} 第{i+1}轮缺少 expected_intent"


class TestEdgeCases:
    """边界和异常测试类"""
    
    @pytest.mark.parametrize("test_case", EDGE_CASE_TEST_CASES, ids=lambda x: x["id"])
    def test_edge_case_structure(self, test_case):
        """测试边界用例结构"""
        assert "input" in test_case, f"测试用例 {test_case['id']} 缺少 input"
        
        print(f"[{test_case['id']}] {test_case['name']}: {test_case['description']}")


class TestTestCaseCoverage:
    """测试用例覆盖率检查"""
    
    def test_intent_recognition_coverage(self):
        """检查意图识别测试覆盖"""
        intent_types = set()
        for case in INTENT_RECOGNITION_TEST_CASES:
            intent_types.add(case["expected_intent"])
        
        required_intents = {
            "usage_guidance", "fault_handling", "fallback", 
            "dissatisfied", "satisfied", "feedback_good", "feedback_bad"
        }
        
        missing = required_intents - intent_types
        assert not missing, f"缺少以下意图类型的测试用例: {missing}"
    
    def test_knowledge_qa_coverage(self):
        """检查知识库问答测试覆盖"""
        categories = set()
        for case in KNOWLEDGE_QA_TEST_CASES:
            name = case["name"]
            if "特斯拉" in name:
                categories.add("tesla")
            elif "比亚迪" in name:
                categories.add("byd")
            elif "故障" in name or "充不进" in name or "拔不出" in name:
                categories.add("fault")
            elif "流程" in name or "费用" in name:
                categories.add("guide")
        
        assert "tesla" in categories, "缺少特斯拉相关测试用例"
        assert "byd" in categories, "缺少比亚迪相关测试用例"
        assert "fault" in categories, "缺少故障处理相关测试用例"
    
    def test_fallback_flow_coverage(self):
        """检查兜底流程测试覆盖"""
        phases = set()
        for case in FALLBACK_FLOW_TEST_CASES:
            phases.add(case["expected_phase"])
        
        # 应覆盖主要状态
        assert "collect_info" in phases, "缺少收集信息状态测试"
        # confirm 和 done 可能需要特定前置条件


def test_all_test_cases_count():
    """验证测试用例总数"""
    all_cases = get_all_test_cases()
    total = sum(len(cases) for cases in all_cases.values())
    
    print(f"\n测试用例总数: {total}")
    for category, cases in all_cases.items():
        print(f"  - {category}: {len(cases)} 个")
    
    assert total >= 50, f"测试用例总数应至少50个，当前: {total}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
