"""
Auto-Research 兜底流程真实测试脚本
真实调用 test_run 工具，根据 AI 回复动态决定下一步
"""
import sys
import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 测试场景 ====================

TEST_SCENARIOS = [
    {
        "id": "S001",
        "name": "优惠券投诉",
        "initial_message": "你们这个垃圾系统，气死我了",
        "expected_problem": "优惠券未使用成功"
    },
    {
        "id": "S002",
        "name": "充电故障",
        "initial_message": "什么垃圾服务，充不进去电",
        "expected_problem": "充电桩故障"
    },
    {
        "id": "S003",
        "name": "退款投诉",
        "initial_message": "我要退款",
        "expected_problem": "退款"
    },
    {
        "id": "S004",
        "name": "模糊投诉",
        "initial_message": "我要投诉",
        "expected_problem": "投诉"
    },
    {
        "id": "S005",
        "name": "情绪激动",
        "initial_message": "垃圾！垃圾！垃圾！",
        "expected_problem": "投诉"
    },
    {
        "id": "S006",
        "name": "中途取消",
        "initial_message": "我要投诉...算了不用了",
        "expected_exit": True  # 期望退出兜底
    },
    {
        "id": "S007",
        "name": "用户纠正",
        "initial_message": "我要投诉，多扣了我钱",
        "correction_message": "不对，是优惠券没用上",
        "expected_problem": "优惠券未使用"
    },
    {
        "id": "S008",
        "name": "分次提供信息",
        "initial_message": "我要投诉",
        "step2_message": "手机 13912345678",
        "step3_message": "车牌京 A12345"
    },
    {
        "id": "S009",
        "name": "语音格式",
        "initial_message": "我要投诉",
        "phone_format": "139。16425678",
        "plate_format": "沪 A Dr 3509"
    },
    {
        "id": "S010",
        "name": "补充信息",
        "initial_message": "我要投诉，多扣钱",
        "step2_message": "手机 13912345678，车牌京 A12345",
        "step3_message": "另外我还有优惠券没用"
    }
]

# ==================== 阶段判断 ====================

def judge_phase(ai_reply: str) -> str:
    """
    根据 AI 回复判断当前阶段

    返回：
    - "ask_problem": 询问阶段（AI 在问用户什么问题）
    - "collect_info": 收集信息阶段（AI 在要手机号车牌）
    - "confirm": 确认阶段（AI 让用户确认总结）
    - "done": 已完成（AI 说 1-3 个工作日）
    - "exit": 已退出（AI 说已取消）
    - "error": 异常回复
    """
    reply_lower = ai_reply.lower()

    # 已完成
    if "1-3 个工作日" in ai_reply or "尽快处理" in ai_reply or "收到您的问题" in ai_reply:
        return "done"

    # 已退出
    if "已取消" in ai_reply or "不需要了" in reply_lower:
        return "exit"

    # 确认阶段
    if "确认" in ai_reply and ("准确吗" in ai_reply or "有误" in ai_reply or "告诉我" in ai_reply):
        return "confirm"

    # 收集信息阶段
    if "手机号" in ai_reply and "车牌号" in ai_reply:
        return "collect_info"

    if "手机号" in ai_reply or "手机" in ai_reply:
        if "车牌" in ai_reply or "车牌号" in ai_reply:
            return "collect_info"

    # 询问阶段
    if "问题" in ai_reply and ("什么情况" in ai_reply or "说说" in ai_reply or "具体" in ai_reply):
        return "ask_problem"

    # 默认
    return "ask_problem"


def generate_next_message(phase: str, scenario: Dict, step: int) -> str:
    """
    根据阶段生成下一条用户消息

    Args:
        phase: 当前阶段
        scenario: 测试场景配置
        step: 当前轮次

    Returns:
        下一条用户消息
    """
    if phase == "ask_problem":
        # 描述具体问题
        if "expected_problem" in scenario:
            return f"我充完电，{scenario['expected_problem']}，多扣了我钱"
        return "充电桩坏了，充不进去电"

    elif phase == "collect_info":
        # 提供手机号和车牌
        if "phone_format" in scenario:
            # 语音格式
            return f"手机号{scenario['phone_format']}。车牌号。{scenario.get('plate_format', '京 A12345')}"
        return "手机 13912345678，车牌京 A12345"

    elif phase == "confirm":
        # 确认或纠正
        if "correction_message" in scenario and step < 3:
            return scenario["correction_message"]
        return "确认"

    return "确认"


# ==================== 测试执行 ====================

def run_scenario_test(scenario: Dict, user_id: str) -> Dict[str, Any]:
    """
    执行单个场景的完整测试

    Args:
        scenario: 测试场景配置
        user_id: 用户 ID（用于保持会话状态）

    Returns:
        测试结果字典
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"开始测试：{scenario['id']} - {scenario['name']}")
    logger.info(f"{'='*60}")

    # 测试记录
    conversation_log = []
    current_phase = "start"
    max_rounds = 8  # 最多 8 轮
    round_num = 0
    test_success = False
    failure_reason = ""

    # 第 1 条消息固定是初始消息
    next_message = scenario["initial_message"]

    while round_num < max_rounds:
        round_num += 1

        # 1. 发送用户消息
        user_message = next_message
        logger.info(f"\n[轮次 {round_num}] 用户：{user_message}")

        # TODO: 这里调用 test_run 工具
        # 由于需要 Coze 的 test_run 工具，这里用伪代码表示
        # 实际执行时需要替换为真实的 test_run 调用

        # ai_reply = call_test_run(user_id, user_message)
        # 暂时用占位符，让 Coze 助手替换为真实调用
        ai_reply = "[需要调用 test_run 工具获取 AI 回复]"

        logger.info(f"[轮次 {round_num}] AI: {ai_reply}")

        # 2. 记录对话
        conversation_log.append({
            "round": round_num,
            "user": user_message,
            "ai": ai_reply
        })

        # 3. 判断阶段
        current_phase = judge_phase(ai_reply)
        logger.info(f"[轮次 {round_num}] 阶段：{current_phase}")

        # 4. 根据阶段决定下一步
        if current_phase == "done":
            logger.info("✅ 工单创建成功，测试通过")
            test_success = True
            break

        elif current_phase == "exit":
            # 检查场景是否期望退出
            if scenario.get("expected_exit"):
                logger.info("✅ 正确退出兜底流程，测试通过")
                test_success = True
            else:
                logger.warning("❌ 意外退出兜底流程")
                failure_reason = "意外退出兜底"
            break

        elif current_phase == "error":
            logger.error("❌ AI 回复异常")
            failure_reason = "AI 回复异常"
            break

        else:
            # 生成下一条消息
            next_message = generate_next_message(current_phase, scenario, round_num)

    # 检查结果
    if not test_success and not failure_reason:
        failure_reason = f"超过最大轮数 ({max_rounds}) 未完成"

    return {
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "success": test_success,
        "failure_reason": failure_reason,
        "rounds": round_num,
        "conversation_log": conversation_log,
        "final_phase": current_phase
    }


# ==================== 批量测试 ====================

def run_all_tests() -> List[Dict[str, Any]]:
    """
    执行所有测试场景

    Returns:
        所有测试结果
    """
    results = []

    for scenario in TEST_SCENARIOS:
        # 每个场景用唯一的 user_id
        user_id = f"test_user_{scenario['id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        result = run_scenario_test(scenario, user_id)
        results.append(result)

    return results


# ==================== 生成报告 ====================

def generate_report(results: List[Dict[str, Any]]) -> str:
    """
    生成测试报告

    Args:
        results: 测试结果列表

    Returns:
        测试报告字符串
    """
    report_lines = []
    report_lines.append("# Auto-Research 兜底流程测试报告")
    report_lines.append(f"\n> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 统计
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    pass_rate = passed / total if total > 0 else 0

    # 汇总
    report_lines.append("\n## 📊 测试结果汇总\n")
    report_lines.append(f"| 场景 ID | 场景名称 | 结果 | 轮数 | 失败原因 |")
    report_lines.append("|--------|---------|------|------|---------|")

    for r in results:
        status = "✅" if r["success"] else "❌"
        fail_reason = r["failure_reason"] if r["failure_reason"] else "-"
        report_lines.append(
            f"| {r['scenario_id']} | {r['scenario_name']} | {status} | {r['rounds']} | {fail_reason} |"
        )

    report_lines.append(f"\n**总计**: {total} 个场景")
    report_lines.append(f"**通过**: {passed} 个")
    report_lines.append(f"**失败**: {failed} 个")
    report_lines.append(f"**通过率**: {pass_rate:.1%}\n")

    # 失败详情
    failed_results = [r for r in results if not r["success"]]
    if failed_results:
        report_lines.append("\n## ❌ 失败分析\n")
        for r in failed_results:
            report_lines.append(f"### {r['scenario_id']} - {r['scenario_name']}")
            report_lines.append(f"**失败原因**: {r['failure_reason']}\n")
            report_lines.append("**对话记录**:")
            for log in r["conversation_log"]:
                report_lines.append(f"- 轮次{log['round']}: 用户\"{log['user']}\" → AI\"{log['ai']}\"")
            report_lines.append("")

    # 完整对话记录
    report_lines.append("\n## 📋 完整对话记录\n")
    for r in results:
        report_lines.append(f"### {r['scenario_id']} - {r['scenario_name']} ({'✅' if r['success'] else '❌'})\n")
        for log in r["conversation_log"]:
            report_lines.append(f"**轮次{log['round']}**")
            report_lines.append(f"- 用户：{log['user']}")
            report_lines.append(f"- AI: {log['ai']}\n")

    return "\n".join(report_lines)


# ==================== 主函数 ====================

def main():
    """主函数"""
    print("=" * 60)
    print("Auto-Research 兜底流程真实测试")
    print("=" * 60)

    # 执行测试
    print("\n开始执行 10 个场景的测试...")
    print("-" * 60)

    results = run_all_tests()

    # 生成报告
    print("\n生成测试报告...")
    report = generate_report(results)

    # 保存报告
    report_path = os.path.join(
        os.path.dirname(__file__),
        '..', 'assets',
        f'AutoResearch-真实测试报告-{datetime.now().strftime("%Y%m%d-%H%M%S")}.md'
    )

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📄 报告已保存到：{report_path}")

    # 打印汇总
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    print(f"\n测试结果：{passed}/{total} 通过 ({passed/total:.1%})" if total > 0 else "")

    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
