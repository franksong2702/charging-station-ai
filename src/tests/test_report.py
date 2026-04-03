"""
充电桩智能客服工作流测试报告生成器
版本: v1.1.0

生成 Markdown 格式的测试报告
"""

import os
import sys
import importlib.util
from typing import Dict, List, Any
from datetime import datetime

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


def generate_test_report() -> str:
    """
    生成测试报告
    
    Returns:
        Markdown 格式的测试报告
    """
    report = []
    
    # 标题
    report.append("# 充电桩智能客服工作流测试报告")
    report.append("")
    report.append(f"**版本**: v1.1.0")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # 概述
    report.append("## 测试概述")
    report.append("")
    
    all_cases = {
        "意图识别": INTENT_RECOGNITION_TEST_CASES,
        "知识库问答": KNOWLEDGE_QA_TEST_CASES,
        "兜底流程": FALLBACK_FLOW_TEST_CASES,
        "评价反馈": FEEDBACK_TEST_CASES,
        "多轮对话": MULTI_TURN_TEST_CASES,
        "边界异常": EDGE_CASE_TEST_CASES,
    }
    
    total = sum(len(cases) for cases in all_cases.values())
    
    report.append(f"| 测试类别 | 用例数量 |")
    report.append(f"|----------|----------|")
    for category, cases in all_cases.items():
        report.append(f"| {category} | {len(cases)} |")
    report.append(f"| **总计** | **{total}** |")
    report.append("")
    
    # v1.1.0 优化重点
    report.append("## v1.1.0 优化重点")
    report.append("")
    report.append("本次版本主要优化了知识库搜索策略，以下是相关的测试用例：")
    report.append("")
    
    # 特斯拉充电测试用例
    report.append("### 特斯拉充电指引测试")
    report.append("")
    tesla_cases = [c for c in KNOWLEDGE_QA_TEST_CASES if "特斯拉" in c["name"]]
    report.append("| ID | 测试名称 | 输入 | 预期关键词 |")
    report.append("|----|----------|------|------------|")
    for case in tesla_cases:
        keywords = ", ".join(case["expected_keywords"]) if case["expected_keywords"] else "无"
        report.append(f"| {case['id']} | {case['name']} | {case['input']['user_message']} | {keywords} |")
    report.append("")
    
    # 比亚迪充电测试用例
    report.append("### 比亚迪充电指引测试")
    report.append("")
    byd_cases = [c for c in KNOWLEDGE_QA_TEST_CASES if "比亚迪" in c["name"]]
    report.append("| ID | 测试名称 | 输入 | 预期关键词 |")
    report.append("|----|----------|------|------------|")
    for case in byd_cases:
        keywords = ", ".join(case["expected_keywords"]) if case["expected_keywords"] else "无"
        report.append(f"| {case['id']} | {case['name']} | {case['input']['user_message']} | {keywords} |")
    report.append("")
    
    # 故障处理测试用例
    report.append("### 故障处理测试")
    report.append("")
    fault_cases = [c for c in KNOWLEDGE_QA_TEST_CASES if "故障" in c["name"] or "充不进" in c["name"] or "拔不出" in c["name"]]
    report.append("| ID | 测试名称 | 输入 | 预期关键词 |")
    report.append("|----|----------|------|------------|")
    for case in fault_cases:
        keywords = ", ".join(case["expected_keywords"]) if case["expected_keywords"] else "无"
        report.append(f"| {case['id']} | {case['name']} | {case['input']['user_message']} | {keywords} |")
    report.append("")
    
    # 意图识别测试用例
    report.append("## 意图识别测试用例")
    report.append("")
    report.append("| ID | 测试名称 | 输入 | 预期意图 | 描述 |")
    report.append("|----|----------|------|----------|------|")
    for case in INTENT_RECOGNITION_TEST_CASES:
        report.append(f"| {case['id']} | {case['name']} | {case['input']['user_message']} | {case['expected_intent']} | {case['description']} |")
    report.append("")
    
    # 兜底流程测试用例
    report.append("## 兜底流程测试用例")
    report.append("")
    report.append("| ID | 测试名称 | 输入 | 预期状态 | 描述 |")
    report.append("|----|----------|------|----------|------|")
    for case in FALLBACK_FLOW_TEST_CASES:
        input_msg = case['input']['user_message']
        phase = case.get('expected_phase', '')
        report.append(f"| {case['id']} | {case['name']} | {input_msg} | {phase} | {case['description']} |")
    report.append("")
    
    # 评价反馈测试用例
    report.append("## 评价反馈测试用例")
    report.append("")
    report.append("| ID | 测试名称 | 输入 | 预期反馈 | 描述 |")
    report.append("|----|----------|------|----------|------|")
    for case in FEEDBACK_TEST_CASES:
        report.append(f"| {case['id']} | {case['name']} | {case['input']['user_message']} | {case['expected_feedback']} | {case['description']} |")
    report.append("")
    
    # 多轮对话测试用例
    report.append("## 多轮对话测试用例")
    report.append("")
    report.append("| ID | 测试名称 | 轮数 | 描述 |")
    report.append("|----|----------|------|------|")
    for case in MULTI_TURN_TEST_CASES:
        turns = len(case['turns'])
        report.append(f"| {case['id']} | {case['name']} | {turns}轮 | {case['description']} |")
    report.append("")
    
    # 边界测试用例
    report.append("## 边界和异常测试用例")
    report.append("")
    report.append("| ID | 测试名称 | 输入 | 描述 |")
    report.append("|----|----------|------|------|")
    for case in EDGE_CASE_TEST_CASES:
        input_msg = case['input']['user_message'][:30] + "..." if len(case['input']['user_message']) > 30 else case['input']['user_message']
        report.append(f"| {case['id']} | {case['name']} | {input_msg} | {case['description']} |")
    report.append("")
    
    # 测试环境
    report.append("## 测试环境")
    report.append("")
    report.append("| 项目 | 说明 |")
    report.append("|------|------|")
    report.append("| Python | 3.12 |")
    report.append("| LangGraph | 1.0 |")
    report.append("| LangChain | 1.0 |")
    report.append("| 测试框架 | pytest |")
    report.append("")
    
    # 运行命令
    report.append("## 运行测试")
    report.append("")
    report.append("```bash")
    report.append("# 运行所有测试")
    report.append("pytest src/tests/test_workflow.py -v")
    report.append("")
    report.append("# 运行指定类别的测试")
    report.append("pytest src/tests/test_workflow.py -v -k \"TestKnowledgeQA\"")
    report.append("")
    report.append("# 生成测试覆盖率报告")
    report.append("pytest src/tests/test_workflow.py -v --cov=graphs --cov-report=html")
    report.append("```")
    report.append("")
    
    return "\n".join(report)


def save_test_report(filepath: str = None):
    """
    保存测试报告到文件
    
    Args:
        filepath: 保存路径，默认为 assets/test_report_v1.1.0.md
    """
    if filepath is None:
        import os
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        filepath = os.path.join(base_path, "assets", "test_report_v1.1.0.md")
    
    report = generate_test_report()
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"测试报告已保存到: {filepath}")
    return filepath


if __name__ == "__main__":
    save_test_report()
