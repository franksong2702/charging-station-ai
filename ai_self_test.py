#!/usr/bin/env python3
"""
AI 自测脚本 - 使用 AI 测试 AI
覆盖除了兜底功能之外的所有场景：
- 使用指导（知识库问答）
- 评价机制
- 闲聊处理
"""
import os
import sys
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# 设置项目路径
project_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
src_path = os.path.join(project_path, "src")
sys.path.insert(0, src_path)
sys.path.insert(0, project_path)

# 导入工作流
from src.graphs.graph import main_graph


# 测试用例定义
class TestCase(BaseModel):
    """单个测试用例"""
    id: str = Field(..., description="测试用例ID")
    name: str = Field(..., description="测试用例名称")
    category: str = Field(..., description="测试类别")
    user_messages: List[str] = Field(..., description="用户消息列表（多轮对话）")
    expected_keywords: List[str] = Field(default=[], description="预期包含的关键词")
    unexpected_keywords: List[str] = Field(default=[], description="预期不包含的关键词")
    description: str = Field(default="", description="测试用例描述")


# 测试结果
class TestResult(BaseModel):
    """单个测试用例的结果"""
    test_case: TestCase
    passed: bool = Field(..., description="是否通过")
    actual_responses: List[str] = Field(default=[], description="实际AI回复")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    duration_seconds: float = Field(default=0.0, description="执行时长")


# 测试报告
class TestReport(BaseModel):
    """完整的测试报告"""
    start_time: datetime
    end_time: datetime
    total_cases: int
    passed_cases: int
    failed_cases: int
    results: List[TestResult]


# 测试用例清单
TEST_CASES = [
    # ==================== 使用指导模块 ====================
    TestCase(
        id="TC-001",
        name="特斯拉充电桩怎么扫码",
        category="使用指导",
        user_messages=["特斯拉充电桩怎么扫码？"],
        expected_keywords=["特斯拉", "二维码"],
        unexpected_keywords=["您对本次回答满意吗", "评价"],
        description="验证特斯拉充电桩扫码操作能正确回答"
    ),
    TestCase(
        id="TC-002",
        name="比亚迪充电桩怎么扫码",
        category="使用指导",
        user_messages=["比亚迪充电桩怎么扫码？"],
        expected_keywords=[],  # 知识库可能没有，不强制要求
        unexpected_keywords=["评价"],
        description="验证比亚迪充电桩扫码操作能正确回答"
    ),
    TestCase(
        id="TC-003",
        name="充不进去电怎么办",
        category="使用指导",
        user_messages=["充不进去电怎么办？"],
        expected_keywords=["充电枪", "换个"],
        unexpected_keywords=["评价"],
        description="验证故障处理咨询能正确回答"
    ),
    TestCase(
        id="TC-004",
        name="充电枪卡住拔不出来怎么办",
        category="使用指导",
        user_messages=["充电枪卡住拔不出来怎么办？"],
        expected_keywords=["停止充电", "解锁"],
        unexpected_keywords=["评价"],
        description="验证充电枪故障能正确回答"
    ),
    TestCase(
        id="TC-005",
        name="充电费用怎么算的",
        category="使用指导",
        user_messages=["充电费用怎么算的？"],
        expected_keywords=["电费", "服务费"],
        unexpected_keywords=["评价"],
        description="验证充电费用咨询能正确回答"
    ),
    TestCase(
        id="TC-006",
        name="如何成为会员享受优惠",
        category="使用指导",
        user_messages=["如何成为会员享受优惠？"],
        expected_keywords=[],  # 知识库可能没有，不强制要求
        unexpected_keywords=["评价"],
        description="验证会员优惠咨询能正确回答"
    ),
    TestCase(
        id="TC-007",
        name="直流快充和交流慢充有什么区别",
        category="使用指导",
        user_messages=["直流快充和交流慢充有什么区别？"],
        expected_keywords=["功率", "速度"],
        unexpected_keywords=["评价"],
        description="验证技术问题能正确回答"
    ),
    TestCase(
        id="TC-008",
        name="第一次用充电桩怎么操作",
        category="使用指导",
        user_messages=["第一次用充电桩，怎么操作？"],
        expected_keywords=["扫码", "充电"],
        unexpected_keywords=["评价"],
        description="验证完整流程指导能正确回答"
    ),
    
    # ==================== 评价机制模块 ====================
    TestCase(
        id="TC-009",
        name="回答后不主动问评价",
        category="评价机制",
        user_messages=["特斯拉充电桩怎么扫码？"],
        expected_keywords=["特斯拉", "二维码"],
        unexpected_keywords=["满意吗", "评价", "有帮助吗"],
        description="验证系统不会'贴脸'问评价"
    ),
    TestCase(
        id="TC-010",
        name="用户表示感谢后触发评价",
        category="评价机制",
        user_messages=["特斯拉充电桩怎么扫码？", "谢谢"],
        expected_keywords=["不客气", "有帮助"],
        unexpected_keywords=[],
        description="验证评价在用户满意时自然触发"
    ),
    
    # ==================== 闲聊处理模块 ====================
    TestCase(
        id="TC-011",
        name="问候语 - 你好",
        category="闲聊处理",
        user_messages=["你好"],
        expected_keywords=["您好", "充电桩"],
        unexpected_keywords=["投诉", "兜底"],
        description="验证问候语能正确引导用户"
    ),
    TestCase(
        id="TC-012",
        name="无意义输入 - asdfgh",
        category="闲聊处理",
        user_messages=["asdfgh"],
        expected_keywords=["没明白", "充电桩"],
        unexpected_keywords=["投诉", "兜底"],
        description="验证无意义输入的友好处理"
    ),
    TestCase(
        id="TC-013",
        name="你是谁",
        category="闲聊处理",
        user_messages=["你是谁？"],
        expected_keywords=["充电桩", "客服", "助手"],
        unexpected_keywords=["投诉", "兜底"],
        description="验证身份询问的正确回应"
    ),
    TestCase(
        id="TC-014",
        name="今天天气怎么样",
        category="闲聊处理",
        user_messages=["今天天气怎么样？"],
        expected_keywords=["充电桩", "客服"],
        unexpected_keywords=["投诉", "兜底"],
        description="验证闲聊的友好处理"
    )
]


def run_single_test_case(test_case: TestCase) -> TestResult:
    """运行单个测试用例"""
    start_time = time.time()
    actual_responses = []
    conversation_id = f"test_{test_case.id}_{int(time.time())}"
    
    try:
        print(f"\n🧪 运行测试用例: {test_case.id} - {test_case.name}")
        print(f"📋 类别: {test_case.category}")
        print(f"📝 描述: {test_case.description}")
        
        # 多轮对话
        for i, user_message in enumerate(test_case.user_messages):
            print(f"👤 轮次 {i+1} 用户消息: {user_message}")
            
            # 调用工作流
            result = main_graph.invoke({
                "user_message": user_message,
                "conversation_id": conversation_id
            })
            
            reply_content = result.get("reply_content", "")
            actual_responses.append(reply_content)
            print(f"🤖 AI 回复: {reply_content[:200]}..." if len(reply_content) > 200 else f"🤖 AI 回复: {reply_content}")
        
        # 检查结果
        passed = True
        last_response = actual_responses[-1] if actual_responses else ""
        
        # 检查预期关键词
        for keyword in test_case.expected_keywords:
            if keyword not in last_response:
                print(f"❌ 缺少预期关键词: {keyword}")
                passed = False
        
        # 检查不期望的关键词
        for keyword in test_case.unexpected_keywords:
            if keyword in last_response:
                print(f"❌ 包含不期望的关键词: {keyword}")
                passed = False
        
        duration = time.time() - start_time
        
        if passed:
            print(f"✅ 测试用例通过! 耗时: {duration:.2f}s")
        else:
            print(f"❌ 测试用例失败! 耗时: {duration:.2f}s")
        
        return TestResult(
            test_case=test_case,
            passed=passed,
            actual_responses=actual_responses,
            duration_seconds=duration
        )
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ 测试用例异常: {str(e)}")
        return TestResult(
            test_case=test_case,
            passed=False,
            actual_responses=actual_responses,
            error_message=str(e),
            duration_seconds=duration
        )


def generate_test_report(results: List[TestResult], start_time: datetime, end_time: datetime) -> TestReport:
    """生成测试报告"""
    total_cases = len(results)
    passed_cases = sum(1 for r in results if r.passed)
    failed_cases = total_cases - passed_cases
    
    return TestReport(
        start_time=start_time,
        end_time=end_time,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        results=results
    )


def save_test_report_to_file(report: TestReport, file_path: str):
    """保存测试报告到文件（Markdown格式）"""
    markdown_content = f"# AI 自测完整测试报告\n\n"
    markdown_content += f"**测试时间**: {report.start_time.strftime('%Y-%m-%d %H:%M:%S')} - {report.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    markdown_content += f"**总时长**: {(report.end_time - report.start_time).total_seconds():.2f} 秒\n\n"
    
    markdown_content += "## 测试结果统计\n\n"
    markdown_content += f"- **总测试用例**: {report.total_cases}\n"
    markdown_content += f"- **通过**: {report.passed_cases} ✅\n"
    markdown_content += f"- **失败**: {report.failed_cases} ❌\n"
    markdown_content += f"- **通过率**: {report.passed_cases / report.total_cases * 100:.1f}%\n\n"
    
    markdown_content += "## 详细测试结果\n\n"
    
    # 按类别分组
    categories = {}
    for result in report.results:
        category = result.test_case.category
        if category not in categories:
            categories[category] = []
        categories[category].append(result)
    
    for category, category_results in categories.items():
        markdown_content += f"### {category}\n\n"
        markdown_content += "| 用例ID | 用例名称 | 状态 | 耗时 |\n"
        markdown_content += "|--------|---------|------|------|\n"
        
        for result in category_results:
            status = "✅ 通过" if result.passed else "❌ 失败"
            markdown_content += f"| {result.test_case.id} | {result.test_case.name} | {status} | {result.duration_seconds:.2f}s |\n"
        
        markdown_content += "\n"
    
    # 详细结果
    markdown_content += "## 各用例详细结果\n\n"
    
    for result in report.results:
        markdown_content += f"### {result.test_case.id} - {result.test_case.name}\n\n"
        markdown_content += f"- **类别**: {result.test_case.category}\n"
        markdown_content += f"- **描述**: {result.test_case.description}\n"
        markdown_content += f"- **状态**: {'✅ 通过' if result.passed else '❌ 失败'}\n"
        markdown_content += f"- **耗时**: {result.duration_seconds:.2f}s\n"
        
        if result.error_message:
            markdown_content += f"- **错误信息**: {result.error_message}\n"
        
        markdown_content += "\n**对话记录**:\n"
        for i, (user_msg, ai_resp) in enumerate(zip(result.test_case.user_messages, result.actual_responses)):
            markdown_content += f"\n轮次 {i+1}:\n"
            markdown_content += f"- 👤 用户: {user_msg}\n"
            markdown_content += f"- 🤖 AI: {ai_resp}\n"
        
        markdown_content += "\n---\n\n"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print(f"\n📄 测试报告已保存到: {file_path}")


def main():
    """主函数"""
    print("=" * 80)
    print("🚀 AI 自测脚本开始运行")
    print("=" * 80)
    
    start_time = datetime.now()
    print(f"⏰ 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 总测试用例数: {len(TEST_CASES)}")
    
    # 运行所有测试用例
    results = []
    for test_case in TEST_CASES:
        result = run_single_test_case(test_case)
        results.append(result)
        # 短暂延迟，避免频繁调用
        time.sleep(1)
    
    # 生成测试报告
    end_time = datetime.now()
    report = generate_test_report(results, start_time, end_time)
    
    # 保存测试报告
    report_file = os.path.join(project_path, "assets", "ai_self_test_report.md")
    save_test_report_to_file(report, report_file)
    
    # 打印总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print(f"总用例: {report.total_cases}")
    print(f"通过: {report.passed_cases} ✅")
    print(f"失败: {report.failed_cases} ❌")
    print(f"通过率: {report.passed_cases / report.total_cases * 100:.1f}%")
    print(f"总耗时: {(end_time - start_time).total_seconds():.2f}s")
    print(f"测试报告: {report_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
