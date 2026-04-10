#!/usr/bin/env python3
"""
真正的多轮对话测试脚本
测试AI vs 工作流AI
完整模拟真实对话，不拆分步骤，不验证单个关键词
"""
import os
import sys
import time
import json
from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, Field

# 设置项目路径
project_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
src_path = os.path.join(project_path, "src")
sys.path.insert(0, src_path)
sys.path.insert(0, project_path)

# 导入工作流
from src.graphs.graph import main_graph


# ============================================================
# 真实多轮对话测试用例
# ============================================================
REAL_CONVERSATION_TESTS = [
    {
        "id": "REAL-001",
        "name": "情绪激动投诉完整流程",
        "description": "用户情绪激动投诉，完整流程：安抚→澄清→收集→确认→创建工单→发邮件",
        "user_messages": [
            "什么垃圾服务！充电桩充不进去电，我都等了半小时了！",
            "太气人了，充电桩坏了也没人修，浪费我时间！",
            "手机13812345678",
            "车牌沪A12345",
            "确认"
        ]
    },
    {
        "id": "REAL-002",
        "name": "用户分步骤提供信息",
        "description": "用户不一次性说完，分步骤提供信息",
        "user_messages": [
            "我要投诉，充电桩有问题",
            "充不进去电，在虹桥火车站充电站",
            "13912345678",
            "沪B88888",
            "对的，没问题"
        ]
    },
    {
        "id": "REAL-003",
        "name": "用户需要更正信息",
        "description": "用户提供信息有误，需要反复更正",
        "user_messages": [
            "我要投诉，充电桩多扣钱了",
            "手机13711112222",
            "不对，手机号是13711113333",
            "车牌沪C12345",
            "车牌错了，应该是沪C12346",
            "确认"
        ]
    },
    {
        "id": "REAL-004",
        "name": "用户中途取消投诉",
        "description": "用户开始投诉后，中途突然想取消",
        "user_messages": [
            "我要投诉，充电桩坏了",
            "手机13612349876",
            "算了，不用处理了"
        ]
    },
    {
        "id": "REAL-005",
        "name": "模糊问题需要多次澄清",
        "description": "用户一开始只说模糊问题，多次澄清后了解清楚",
        "user_messages": [
            "充不进去电",
            "在浦东机场充电站",
            "就是3号桩，屏幕显示故障",
            "13598765432",
            "沪D98765",
            "对的，确认"
        ]
    }
]


def run_real_conversation_test(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """
    运行单个真实多轮对话测试
    """
    test_id = test_case["id"]
    test_name = test_case["name"]
    user_messages = test_case["user_messages"]
    
    print(f"\n{'='*80}")
    print(f"🎭 真实多轮对话测试: {test_id} - {test_name}")
    print(f"📝 描述: {test_case['description']}")
    print(f"{'='*80}")
    
    conversation_id = f"real_test_{test_id}_{int(time.time())}"
    conversation_history = []
    all_ai_replies = []
    
    start_time = time.time()
    
    print(f"\n👤 测试用户ID: {conversation_id}")
    print(f"🗣️  对话轮次: {len(user_messages)} 轮\n")
    
    try:
        for i, user_message in enumerate(user_messages):
            print(f"--- 第 {i+1} 轮对话 ---")
            print(f"👤 用户: {user_message}")
            
            # 调用工作流
            result = main_graph.invoke({
                "user_message": user_message,
                "conversation_id": conversation_id
            })
            
            ai_reply = result.get("reply_content", "")
            print(f"🤖 工作流AI: {ai_reply}")
            print()
            
            # 保存对话
            conversation_history.append({
                "turn": i + 1,
                "role": "user",
                "content": user_message
            })
            conversation_history.append({
                "turn": i + 1,
                "role": "assistant",
                "content": ai_reply
            })
            all_ai_replies.append({
                "turn": i + 1,
                "user_message": user_message,
                "ai_reply": ai_reply,
                "full_state": result
            })
            
            # 短暂暂停
            time.sleep(1)
        
        # 判断是否成功（完整跑完对话
        success = len(all_ai_replies) == len(user_messages)
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        print(f"✅ 测试完成！")
        print(f"⏱️  总耗时: {duration} 秒")
        print(f"💬  对话总轮次: {len(conversation_history)//2} 轮")
        
        return {
            "id": test_id,
            "name": test_name,
            "description": test_case["description"],
            "success": success,
            "duration": duration,
            "conversation_history": conversation_history,
            "all_ai_replies": all_ai_replies,
            "error": None
        }
        
    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        print(f"❌ 测试异常: {e}")
        import traceback
        print(traceback.format_exc())
        
        return {
            "id": test_id,
            "name": test_name,
            "description": test_case["description"],
            "success": False,
            "duration": duration,
            "conversation_history": conversation_history,
            "all_ai_replies": all_ai_replies,
            "error": str(e)
        }


def generate_real_conversation_report(
    all_results: List[Dict[str, Any]],
    start_time: float,
    end_time: float
) -> str:
    """
    生成真实多轮对话测试报告
    """
    total_duration = round(end_time - start_time, 2)
    total_tests = len(all_results)
    passed_tests = len([r for r in all_results if r["success"]])
    failed_tests = total_tests - passed_tests
    pass_rate = round((passed_tests / total_tests * 100), 1) if total_tests > 0 else 0
    
    report_lines = []
    report_lines.append("# 🎭 充电桩智能客服系统 - 真实多轮对话测试报告")
    report_lines.append("")
    report_lines.append(f"**测试执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**总测试时长**: {total_duration} 秒")
    report_lines.append("")
    report_lines.append("## 📊 总体测试结果")
    report_lines.append("")
    report_lines.append("| 指标 | 数值 |")
    report_lines.append("|------|------|")
    report_lines.append(f"| 总测试用例数 | {total_tests} |")
    report_lines.append(f"| ✅ 完整跑完 | {passed_tests} |")
    report_lines.append(f"| ❌ 异常 | {failed_tests} |")
    report_lines.append(f"| 📈 成功率 | {pass_rate}% |")
    report_lines.append("")
    
    report_lines.append("## 📝 详细测试结果")
    report_lines.append("")
    
    for result in all_results:
        status_emoji = "✅" if result["success"] else "❌"
        report_lines.append(f"### {status_emoji} {result['id']}: {result['name']}")
        report_lines.append("")
        report_lines.append(f"- **描述**: {result['description']}")
        report_lines.append(f"- **总耗时**: {result['duration']} 秒")
        report_lines.append("")
        
        if not result["success"] and result.get("error"):
            report_lines.append(f"**错误信息**: {result['error']}")
            report_lines.append("")
        
        report_lines.append("#### 💬 完整对话历史")
        report_lines.append("")
        
        for msg in result.get("conversation_history", []):
            role_emoji = "👤" if msg["role"] == "user" else "🤖"
            turn_info = f" (第{msg['turn']}轮)" if "turn" in msg else ""
            report_lines.append(f"{role_emoji} **{msg['role']}{turn_info}: {msg['content']}")
        report_lines.append("")
    
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("*报告由真实多轮对话测试脚本自动生成 - 测试AI vs 工作流AI*")
    
    return "\n".join(report_lines)


def main():
    """
    主函数：运行真实多轮对话测试
    """
    print("🚀 开始真实多轮对话测试...")
    print(f"📋 加载 {len(REAL_CONVERSATION_TESTS)} 个真实多轮对话测试用例")
    
    start_time = time.time()
    
    all_results = []
    
    # 运行所有测试
    for test_case in REAL_CONVERSATION_TESTS:
        result = run_real_conversation_test(test_case)
        all_results.append(result)
    
    end_time = time.time()
    
    # 生成报告
    print("\n" + "="*80)
    print("📝 生成真实多轮对话测试报告...")
    
    report = generate_real_conversation_report(
        all_results=all_results,
        start_time=start_time,
        end_time=end_time
    )
    
    # 保存报告
    report_path = os.path.join(project_path, "assets", "真实多轮对话测试报告.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"✅ 真实多轮对话测试报告已保存到: {report_path}")
    
    # 输出总结
    total_tests = len(all_results)
    passed_tests = len([r for r in all_results if r["success"]])
    failed_tests = total_tests - passed_tests
    pass_rate = round((passed_tests / total_tests * 100), 1) if total_tests > 0 else 0
    total_duration = round(end_time - start_time, 2)
    
    print("\n" + "="*80)
    print("📊 真实多轮对话测试总结")
    print("="*80)
    print(f"总测试用例数: {total_tests}")
    print(f"✅ 完整跑完: {passed_tests}")
    print(f"❌ 异常: {failed_tests}")
    print(f"📈 成功率: {pass_rate}%")
    print(f"⏱️  总耗时: {total_duration} 秒")
    print("="*80)
    
    print("\n🎉 真实多轮对话测试完成！")
    print(f"📖 查看完整报告: {report_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
