#!/usr/bin/env python3
"""
完整的 AI 测试脚本 - 包含所有场景
测试内容：
1. 使用指导（知识库查询）
2. 评价机制
3. 闲聊处理
4. 兜底流程（可选）

特点：
- 详细的时间记录（每个用例的开始/结束时间）
- 真实调用工作流和大模型
- 生成专业的、给客户的测试报告
"""
import os
import sys
import time
import json
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


# ==================== 数据模型定义 ====================
class TestCaseStep(BaseModel):
    """单个测试步骤"""
    user_message: str = Field(..., description="用户消息")
    expected_keywords: List[str] = Field(default=[], description="预期包含的关键词")
    unexpected_keywords: List[str] = Field(default=[], description="预期不包含的关键词")


class TestCase(BaseModel):
    """单个测试用例"""
    id: str = Field(..., description="测试用例ID")
    name: str = Field(..., description="测试用例名称")
    category: str = Field(..., description="测试类别")
    description: str = Field(..., description="测试用例描述")
    steps: List[TestCaseStep] = Field(..., description="测试步骤列表")


class TestStepResult(BaseModel):
    """单个测试步骤的结果"""
    step_index: int = Field(..., description="步骤索引")
    user_message: str = Field(..., description="用户消息")
    actual_response: str = Field(..., description="实际AI回复")
    passed: bool = Field(..., description="是否通过")
    duration_seconds: float = Field(..., description="执行时长")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class TestCaseResult(BaseModel):
    """单个测试用例的结果"""
    test_case: TestCase = Field(..., description="测试用例")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    duration_seconds: float = Field(..., description="总时长")
    step_results: List[TestStepResult] = Field(..., description="各步骤结果")
    overall_passed: bool = Field(..., description="整体是否通过")


class TestReport(BaseModel):
    """完整的测试报告"""
    test_start_time: datetime = Field(..., description="测试开始时间")
    test_end_time: datetime = Field(..., description="测试结束时间")
    total_duration_seconds: float = Field(..., description="总测试时长")
    total_test_cases: int = Field(..., description="总测试用例数")
    passed_test_cases: int = Field(..., description="通过的测试用例数")
    failed_test_cases: int = Field(..., description="失败的测试用例数")
    pass_rate: float = Field(..., description="通过率")
    test_case_results: List[TestCaseResult] = Field(..., description="各测试用例结果")


# ==================== 测试用例定义 ====================
COMPLETE_TEST_CASES = [
    # ==================== 使用指导模块 ====================
    TestCase(
        id="UC-001",
        name="特斯拉充电桩怎么扫码",
        category="使用指导",
        description="验证特斯拉充电桩扫码操作能正确回答",
        steps=[
            TestCaseStep(
                user_message="特斯拉充电桩怎么扫码？",
                expected_keywords=["特斯拉", "二维码"],
                unexpected_keywords=["评价", "满意吗"]
            )
        ]
    ),
    TestCase(
        id="UC-002",
        name="比亚迪充电桩怎么扫码",
        category="使用指导",
        description="验证比亚迪充电桩扫码操作能正确回答",
        steps=[
            TestCaseStep(
                user_message="比亚迪充电桩怎么扫码？",
                expected_keywords=[],
                unexpected_keywords=["评价"]
            )
        ]
    ),
    TestCase(
        id="UC-003",
        name="充不进去电怎么办",
        category="使用指导",
        description="验证故障处理咨询能正确回答",
        steps=[
            TestCaseStep(
                user_message="充不进去电怎么办？",
                expected_keywords=["充电枪", "换个"],
                unexpected_keywords=["评价"]
            )
        ]
    ),
    TestCase(
        id="UC-004",
        name="充电枪卡住拔不出来怎么办",
        category="使用指导",
        description="验证充电枪故障能正确回答",
        steps=[
            TestCaseStep(
                user_message="充电枪卡住拔不出来怎么办？",
                expected_keywords=["停止充电", "解锁"],
                unexpected_keywords=["评价"]
            )
        ]
    ),
    TestCase(
        id="UC-005",
        name="充电费用怎么算的",
        category="使用指导",
        description="验证充电费用咨询能正确回答",
        steps=[
            TestCaseStep(
                user_message="充电费用怎么算的？",
                expected_keywords=["电费", "服务费"],
                unexpected_keywords=["评价"]
            )
        ]
    ),
    TestCase(
        id="UC-006",
        name="如何成为会员享受优惠",
        category="使用指导",
        description="验证会员优惠咨询能正确回答",
        steps=[
            TestCaseStep(
                user_message="如何成为会员享受优惠？",
                expected_keywords=[],
                unexpected_keywords=["评价"]
            )
        ]
    ),
    TestCase(
        id="UC-007",
        name="直流快充和交流慢充有什么区别",
        category="使用指导",
        description="验证技术问题能正确回答",
        steps=[
            TestCaseStep(
                user_message="直流快充和交流慢充有什么区别？",
                expected_keywords=["功率", "速度"],
                unexpected_keywords=["评价"]
            )
        ]
    ),
    TestCase(
        id="UC-008",
        name="第一次用充电桩怎么操作",
        category="使用指导",
        description="验证完整流程指导能正确回答",
        steps=[
            TestCaseStep(
                user_message="第一次用充电桩，怎么操作？",
                expected_keywords=["扫码", "充电"],
                unexpected_keywords=["评价"]
            )
        ]
    ),
    
    # ==================== 评价机制模块 ====================
    TestCase(
        id="EV-001",
        name="回答后不主动问评价",
        category="评价机制",
        description="验证系统不会'贴脸'问评价",
        steps=[
            TestCaseStep(
                user_message="特斯拉充电桩怎么扫码？",
                expected_keywords=["特斯拉", "二维码"],
                unexpected_keywords=["满意吗", "评价", "有帮助吗"]
            )
        ]
    ),
    TestCase(
        id="EV-002",
        name="用户表示感谢后触发评价",
        category="评价机制",
        description="验证评价在用户满意时自然触发",
        steps=[
            TestCaseStep(
                user_message="特斯拉充电桩怎么扫码？",
                expected_keywords=["特斯拉", "二维码"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="谢谢",
                expected_keywords=["不客气", "有帮助"],
                unexpected_keywords=[]
            )
        ]
    ),
    
    # ==================== 闲聊处理模块 ====================
    TestCase(
        id="CH-001",
        name="问候语 - 你好",
        category="闲聊处理",
        description="验证问候语能正确引导用户",
        steps=[
            TestCaseStep(
                user_message="你好",
                expected_keywords=["您好", "充电桩"],
                unexpected_keywords=["投诉", "兜底"]
            )
        ]
    ),
    TestCase(
        id="CH-002",
        name="无意义输入 - asdfgh",
        category="闲聊处理",
        description="验证无意义输入的友好处理",
        steps=[
            TestCaseStep(
                user_message="asdfgh",
                expected_keywords=["没明白", "充电桩"],
                unexpected_keywords=["投诉", "兜底"]
            )
        ]
    ),
    TestCase(
        id="CH-003",
        name="你是谁",
        category="闲聊处理",
        description="验证身份询问的正确回应",
        steps=[
            TestCaseStep(
                user_message="你是谁？",
                expected_keywords=["充电桩", "客服", "助手"],
                unexpected_keywords=["投诉", "兜底"]
            )
        ]
    ),
    TestCase(
        id="CH-004",
        name="今天天气怎么样",
        category="闲聊处理",
        description="验证闲聊的友好处理",
        steps=[
            TestCaseStep(
                user_message="今天天气怎么样？",
                expected_keywords=["充电桩", "客服"],
                unexpected_keywords=["投诉", "兜底"]
            )
        ]
    ),
    
    # ==================== 兜底流程模块（深度多轮对话测试） ====================
    TestCase(
        id="DF-001",
        name="情绪激动投诉完整流程",
        category="兜底流程",
        description="用户情绪激动投诉，经历安抚→澄清→收集→确认→创建工单的完整流程",
        steps=[
            TestCaseStep(
                user_message="什么垃圾服务！充电桩充不进去电，我都等了半小时了！",
                expected_keywords=["非常抱歉", "不好的体验"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="太气人了，充电桩坏了也没人修，浪费我时间！",
                expected_keywords=[],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="手机13812345678",
                expected_keywords=["手机号", "已记录"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="车牌沪A12345",
                expected_keywords=["车牌号", "已记录"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="确认",
                expected_keywords=["确认", "收到", "工单"],
                unexpected_keywords=[]
            )
        ]
    ),
    TestCase(
        id="DF-002",
        name="用户分步骤提供信息",
        category="兜底流程",
        description="用户不一次性说完，而是分步骤提供问题、手机号、车牌",
        steps=[
            TestCaseStep(
                user_message="我要投诉，充电桩有问题",
                expected_keywords=["非常抱歉", "不好的体验"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="充不进去电，在虹桥火车站充电站",
                expected_keywords=[],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="13912345678",
                expected_keywords=["手机号", "已记录"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="沪B88888",
                expected_keywords=["车牌号", "已记录"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="对的，没问题",
                expected_keywords=["确认", "收到"],
                unexpected_keywords=[]
            )
        ]
    ),
    TestCase(
        id="DF-003",
        name="用户需要更正信息",
        category="兜底流程",
        description="用户提供的信息有误，需要反复更正",
        steps=[
            TestCaseStep(
                user_message="我要投诉，充电桩多扣钱了",
                expected_keywords=["非常抱歉", "不好的体验"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="手机13711112222",
                expected_keywords=["手机号", "已记录"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="不对，手机号是13711113333",
                expected_keywords=["手机号", "已记录", "更新"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="车牌沪C12345",
                expected_keywords=["车牌号", "已记录"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="车牌错了，应该是沪C12346",
                expected_keywords=["车牌号", "已记录", "更新"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="确认",
                expected_keywords=["确认", "收到"],
                unexpected_keywords=[]
            )
        ]
    ),
    TestCase(
        id="DF-004",
        name="用户中途取消投诉",
        category="兜底流程",
        description="用户开始投诉后，中途突然想取消",
        steps=[
            TestCaseStep(
                user_message="我要投诉，充电桩坏了",
                expected_keywords=["非常抱歉", "不好的体验"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="手机13612349876",
                expected_keywords=["手机号", "已记录"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="算了，不用处理了",
                expected_keywords=["好的", "已取消"],
                unexpected_keywords=["确认", "工单"]
            )
        ]
    ),
    TestCase(
        id="DF-005",
        name="模糊问题需要多次澄清",
        category="兜底流程",
        description="用户一开始只说模糊问题，系统需要多次追问才能了解清楚",
        steps=[
            TestCaseStep(
                user_message="充不进去电",
                expected_keywords=["非常抱歉", "不好的体验", "具体"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="在浦东机场充电站",
                expected_keywords=[],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="就是3号桩，屏幕显示故障",
                expected_keywords=[],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="13598765432",
                expected_keywords=["手机号", "已记录"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="沪D98765",
                expected_keywords=["车牌号", "已记录"],
                unexpected_keywords=[]
            ),
            TestCaseStep(
                user_message="对的，确认",
                expected_keywords=["确认", "收到"],
                unexpected_keywords=[]
            )
        ]
    )
]


# ==================== 测试执行函数 ====================
def run_test_case(test_case: TestCase) -> TestCaseResult:
    """运行单个测试用例"""
    start_time = datetime.now()
    print(f"\n{'='*80}")
    print(f"🧪 测试用例: {test_case.id} - {test_case.name}")
    print(f"📋 类别: {test_case.category}")
    print(f"📝 描述: {test_case.description}")
    print(f"⏰ 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    conversation_id = f"test_{test_case.id}_{int(time.time())}"
    step_results = []
    overall_passed = True
    
    for i, step in enumerate(test_case.steps):
        step_start_time = time.time()
        print(f"\n📍 步骤 {i+1}/{len(test_case.steps)}")
        print(f"👤 用户消息: {step.user_message}")
        
        try:
            # 调用工作流
            result = main_graph.invoke({
                "user_message": step.user_message,
                "conversation_id": conversation_id
            })
            
            actual_response = result.get("reply_content", "")
            print(f"🤖 AI 回复: {actual_response[:200]}..." if len(actual_response) > 200 else f"🤖 AI 回复: {actual_response}")
            
            # 验证结果
            step_passed = True
            
            # 检查预期关键词
            for keyword in step.expected_keywords:
                if keyword not in actual_response:
                    print(f"❌ 缺少预期关键词: {keyword}")
                    step_passed = False
            
            # 检查不期望的关键词
            for keyword in step.unexpected_keywords:
                if keyword in actual_response:
                    print(f"❌ 包含不期望的关键词: {keyword}")
                    step_passed = False
            
            if step_passed:
                print(f"✅ 步骤 {i+1} 通过")
            else:
                print(f"❌ 步骤 {i+1} 失败")
                overall_passed = False
            
            step_duration = time.time() - step_start_time
            print(f"⏱️  步骤耗时: {step_duration:.2f}秒")
            
            step_results.append(TestStepResult(
                step_index=i,
                user_message=step.user_message,
                actual_response=actual_response,
                passed=step_passed,
                duration_seconds=step_duration
            ))
            
        except Exception as e:
            step_duration = time.time() - step_start_time
            print(f"❌ 步骤 {i+1} 异常: {str(e)}")
            overall_passed = False
            step_results.append(TestStepResult(
                step_index=i,
                user_message=step.user_message,
                actual_response="",
                passed=False,
                duration_seconds=step_duration,
                error_message=str(e)
            ))
    
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    print(f"\n{'='*80}")
    if overall_passed:
        print(f"✅ 测试用例 {test_case.id} 通过")
    else:
        print(f"❌ 测试用例 {test_case.id} 失败")
    print(f"⏰ 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  总耗时: {total_duration:.2f}秒")
    print(f"{'='*80}")
    
    return TestCaseResult(
        test_case=test_case,
        start_time=start_time,
        end_time=end_time,
        duration_seconds=total_duration,
        step_results=step_results,
        overall_passed=overall_passed
    )


def generate_markdown_report(test_report: TestReport) -> str:
    """生成 Markdown 格式的测试报告"""
    markdown = "# 充电桩智能客服系统 - 完整测试报告\n\n"
    markdown += f"**测试执行时间**: {test_report.test_start_time.strftime('%Y-%m-%d %H:%M:%S')} - {test_report.test_end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    markdown += f"**总测试时长**: {test_report.total_duration_seconds:.2f} 秒\n\n"
    
    # 测试结果统计
    markdown += "## 测试结果统计\n\n"
    markdown += "| 指标 | 数值 |\n"
    markdown += "|------|------|\n"
    markdown += f"| 总测试用例数 | {test_report.total_test_cases} |\n"
    markdown += f"| 通过 | {test_report.passed_test_cases} ✅ |\n"
    markdown += f"| 失败 | {test_report.failed_test_cases} ❌ |\n"
    markdown += f"| 通过率 | {test_report.pass_rate:.1f}% |\n"
    markdown += "\n"
    
    # 按类别统计
    markdown += "## 按类别统计\n\n"
    
    categories = {}
    for result in test_report.test_case_results:
        category = result.test_case.category
        if category not in categories:
            categories[category] = {"total": 0, "passed": 0}
        categories[category]["total"] += 1
        if result.overall_passed:
            categories[category]["passed"] += 1
    
    markdown += "| 类别 | 总用例数 | 通过 | 失败 | 通过率 |\n"
    markdown += "|------|---------|------|------|--------|\n"
    for category, stats in categories.items():
        pass_rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        markdown += f"| {category} | {stats['total']} | {stats['passed']} ✅ | {stats['total'] - stats['passed']} ❌ | {pass_rate:.1f}% |\n"
    markdown += "\n"
    
    # 详细测试结果
    markdown += "## 详细测试结果\n\n"
    
    for result in test_report.test_case_results:
        test_case = result.test_case
        status = "✅ 通过" if result.overall_passed else "❌ 失败"
        
        markdown += f"### {test_case.id} - {test_case.name}\n\n"
        markdown += f"- **类别**: {test_case.category}\n"
        markdown += f"- **描述**: {test_case.description}\n"
        markdown += f"- **状态**: {status}\n"
        markdown += f"- **开始时间**: {result.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        markdown += f"- **结束时间**: {result.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        markdown += f"- **总耗时**: {result.duration_seconds:.2f}秒\n\n"
        
        markdown += "**测试步骤**:\n\n"
        for step_result in result.step_results:
            step_status = "✅ 通过" if step_result.passed else "❌ 失败"
            markdown += f"#### 步骤 {step_result.step_index + 1}\n\n"
            markdown += f"- **用户消息**: {step_result.user_message}\n"
            markdown += f"- **AI 回复**: {step_result.actual_response}\n"
            markdown += f"- **状态**: {step_status}\n"
            markdown += f"- **耗时**: {step_result.duration_seconds:.2f}秒\n"
            if step_result.error_message:
                markdown += f"- **错误信息**: {step_result.error_message}\n"
            markdown += "\n"
        
        markdown += "---\n\n"
    
    return markdown


def main():
    """主函数"""
    print("=" * 80)
    print("🚀 充电桩智能客服系统 - 完整测试开始")
    print("=" * 80)
    
    test_start_time = datetime.now()
    print(f"⏰ 测试开始时间: {test_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 总测试用例数: {len(COMPLETE_TEST_CASES)}")
    
    # 运行所有测试用例
    test_case_results = []
    for test_case in COMPLETE_TEST_CASES:
        result = run_test_case(test_case)
        test_case_results.append(result)
        # 短暂延迟，避免频繁调用
        time.sleep(0.5)
    
    # 生成测试报告
    test_end_time = datetime.now()
    total_duration = (test_end_time - test_start_time).total_seconds()
    total_test_cases = len(test_case_results)
    passed_test_cases = sum(1 for r in test_case_results if r.overall_passed)
    failed_test_cases = total_test_cases - passed_test_cases
    pass_rate = passed_test_cases / total_test_cases * 100 if total_test_cases > 0 else 0
    
    test_report = TestReport(
        test_start_time=test_start_time,
        test_end_time=test_end_time,
        total_duration_seconds=total_duration,
        total_test_cases=total_test_cases,
        passed_test_cases=passed_test_cases,
        failed_test_cases=failed_test_cases,
        pass_rate=pass_rate,
        test_case_results=test_case_results
    )
    
    # 保存测试报告
    report_file = os.path.join(project_path, "assets", "完整测试报告.md")
    markdown_report = generate_markdown_report(test_report)
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(markdown_report)
    
    # 打印总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print(f"总用例: {test_report.total_test_cases}")
    print(f"通过: {test_report.passed_test_cases} ✅")
    print(f"失败: {test_report.failed_test_cases} ❌")
    print(f"通过率: {test_report.pass_rate:.1f}%")
    print(f"总耗时: {test_report.total_duration_seconds:.2f}秒")
    print(f"测试报告: {report_file}")
    print("=" * 80)
    
    print(f"\n✅ 完整测试完成！测试报告已保存到: {report_file}")


if __name__ == "__main__":
    main()
