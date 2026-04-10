#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coze 平台工作流 API 完整测试脚本
支持本地运行模式和 API 模式
"""
import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目根目录到 PYTHONPATH
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, PROJECT_ROOT)

# ========================================
# 测试配置
# ========================================
COZE_API_URL = "https://wp5bsz5qfm.coze.site/run"
WORKFLOW_ID = "7619179949030801458"

# ========================================
# 本地运行模式导入
# ========================================
def load_main_graph():
    """加载主图用于本地运行"""
    from src.main import service
    return service

# ========================================
# 测试用例定义
# ========================================
TEST_CASES = [
    # 场景 1: 使用指导
    {
        "category": "使用指导",
        "subcategory": "正常问答",
        "cases": [
            {
                "id": "USAGE-001",
                "name": "特斯拉充电桩怎么扫码",
                "description": "验证特斯拉充电桩扫码操作能正确回答",
                "user_message": "特斯拉充电桩怎么扫码？",
                "expected_keywords": ["扫码", "二维码", "充电桩"],
                "unexpected_keywords": ["兜底", "投诉", "协商"]
            },
            {
                "id": "USAGE-002",
                "name": "第一次用充电桩怎么操作",
                "description": "验证新用户使用指导能正确回答",
                "user_message": "第一次用充电桩怎么操作？",
                "expected_keywords": ["使用", "操作", "步骤"],
                "unexpected_keywords": ["兜底", "投诉", "协商"]
            },
            {
                "id": "USAGE-003",
                "name": "充电费用怎么算的",
                "description": "验证费用咨询能正确回答",
                "user_message": "充电费用怎么算的？",
                "expected_keywords": ["费用", "价格", "元"],
                "unexpected_keywords": ["兜底", "投诉", "协商"]
            }
        ]
    },
    
    # 场景 2: 故障处理
    {
        "category": "故障处理",
        "subcategory": "正常问答",
        "cases": [
            {
                "id": "FAULT-001",
                "name": "充不进去电怎么办",
                "description": "验证充电故障咨询能正确回答",
                "user_message": "充不进去电怎么办？",
                "expected_keywords": ["检查", "故障", "充电"],
                "unexpected_keywords": ["兜底", "投诉", "协商"]
            },
            {
                "id": "FAULT-002",
                "name": "充电枪卡住拔不出来怎么办",
                "description": "验证充电枪故障咨询能正确回答",
                "user_message": "充电枪卡住拔不出来怎么办？",
                "expected_keywords": ["卡住", "拔", "充电枪"],
                "unexpected_keywords": ["兜底", "投诉", "协商"]
            },
            {
                "id": "FAULT-003",
                "name": "直流快充和交流慢充有什么区别",
                "description": "验证技术问题咨询能正确回答",
                "user_message": "直流快充和交流慢充有什么区别？",
                "expected_keywords": ["直流", "交流", "快充", "慢充"],
                "unexpected_keywords": ["兜底", "投诉", "协商"]
            }
        ]
    },
    
    # 场景 3: 协商处理
    {
        "category": "协商处理",
        "subcategory": "退款/扣费咨询",
        "cases": [
            {
                "id": "NEG-001",
                "name": "我要退款",
                "description": "验证退款咨询能进入协商处理",
                "user_message": "我要退款",
                "expected_keywords": ["协商", "问清楚", "方案", "退款"],
                "unexpected_keywords": []
            },
            {
                "id": "NEG-002",
                "name": "多扣钱了",
                "description": "验证扣费咨询能进入协商处理",
                "user_message": "多扣钱了",
                "expected_keywords": ["协商", "问清楚", "方案", "扣钱"],
                "unexpected_keywords": []
            },
            {
                "id": "NEG-003",
                "name": "优惠券没用上",
                "description": "验证优惠券咨询能进入协商处理",
                "user_message": "优惠券没用上",
                "expected_keywords": ["协商", "问清楚", "方案", "优惠券"],
                "unexpected_keywords": []
            }
        ]
    },
    
    # 场景 4: 投诉兜底
    {
        "category": "投诉兜底",
        "subcategory": "强烈不满",
        "cases": [
            {
                "id": "FALLBACK-001",
                "name": "垃圾服务",
                "description": "验证强烈不满能进入兜底流程",
                "user_message": "垃圾服务！",
                "expected_keywords": ["兜底", "安抚", "手机号", "车牌号"],
                "unexpected_keywords": []
            },
            {
                "id": "FALLBACK-002",
                "name": "我要投诉",
                "description": "验证明确投诉能进入兜底流程",
                "user_message": "我要投诉",
                "expected_keywords": ["兜底", "安抚", "手机号", "车牌号"],
                "unexpected_keywords": []
            },
            {
                "id": "FALLBACK-003",
                "name": "气死我了",
                "description": "验证情绪激动能进入兜底流程",
                "user_message": "气死我了！充电桩坏了也没人修！",
                "expected_keywords": ["兜底", "安抚", "手机号", "车牌号"],
                "unexpected_keywords": []
            }
        ]
    },
    
    # 场景 5: 评价反馈
    {
        "category": "评价反馈",
        "subcategory": "满意/不满意",
        "cases": [
            {
                "id": "FEEDBACK-001",
                "name": "用户表示感谢",
                "description": "验证用户感谢后能触发评价",
                "user_message": "谢谢",
                "expected_keywords": ["评价", "有帮助", "没有帮助"],
                "unexpected_keywords": ["兜底", "投诉", "协商"]
            },
            {
                "id": "FEEDBACK-002",
                "name": "用户表示满意",
                "description": "验证用户满意能正确处理",
                "user_message": "很满意",
                "expected_keywords": ["满意", "感谢"],
                "unexpected_keywords": ["兜底", "投诉", "协商"]
            },
            {
                "id": "FEEDBACK-003",
                "name": "用户表示没用",
                "description": "验证用户不满意能正确处理",
                "user_message": "没用",
                "expected_keywords": ["抱歉", "没帮助"],
                "unexpected_keywords": ["兜底", "投诉", "协商"]
            }
        ]
    }
]

# ========================================
# 测试执行函数
# ========================================
def call_api(user_message: str, user_id: str = "test_user_001") -> Dict[str, Any]:
    """调用 Coze API"""
    import requests
    
    payload = {
        "user_message": user_message,
        "user_id": user_id
    }
    
    try:
        response = requests.post(
            COZE_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        return {
            "success": True,
            "data": response.json(),
            "status_code": response.status_code
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        }

def run_local(user_message: str, user_id: str = "test_user_001") -> Dict[str, Any]:
    """本地运行模式"""
    try:
        service = load_main_graph()
        
        # 同步调用
        import asyncio
        result = asyncio.run(service.run({
            "user_message": user_message,
            "user_id": user_id
        }))
        
        return {
            "success": True,
            "data": result,
            "status_code": 200
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "status_code": 500
        }

def check_result(ai_reply: str, expected_keywords: List[str], unexpected_keywords: List[str]) -> Dict[str, Any]:
    """检查测试结果"""
    checks = {
        "expected_found": [],
        "expected_missing": [],
        "unexpected_found": [],
        "unexpected_not_found": []
    }
    
    # 检查期望关键词
    for keyword in expected_keywords:
        if keyword in ai_reply:
            checks["expected_found"].append(keyword)
        else:
            checks["expected_missing"].append(keyword)
    
    # 检查不期望关键词
    for keyword in unexpected_keywords:
        if keyword in ai_reply:
            checks["unexpected_found"].append(keyword)
        else:
            checks["unexpected_not_found"].append(keyword)
    
    # 判定通过：所有期望关键词至少找到一个，且没有不期望关键词
    has_expected = len(checks["expected_found"]) > 0 or len(expected_keywords) == 0
    no_unexpected = len(checks["unexpected_found"]) == 0
    
    return {
        "passed": has_expected and no_unexpected,
        "checks": checks
    }

# ========================================
# 报告生成
# ========================================
def generate_markdown_report(results: List[Dict[str, Any]], start_time: float, end_time: float, mode: str) -> str:
    """生成 Markdown 格式的测试报告"""
    total_cases = len(results)
    passed_cases = sum(1 for r in results if r.get("passed", False))
    api_success = sum(1 for r in results if r.get("api_success", False))
    
    # 按类别统计
    category_stats = {}
    for result in results:
        category = result["category"]
        if category not in category_stats:
            category_stats[category] = {"total": 0, "passed": 0, "failed": 0}
        category_stats[category]["total"] += 1
        if result.get("passed", False):
            category_stats[category]["passed"] += 1
        else:
            category_stats[category]["failed"] += 1
    
    # 生成报告
    report_lines = []
    report_lines.append(f"# 🚀 Coze 平台工作流 {mode} 完整测试报告\n")
    report_lines.append(f"**测试执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if mode == "API":
        report_lines.append(f"**API 地址**: {COZE_API_URL}")
    report_lines.append(f"**工作流 ID**: {WORKFLOW_ID}")
    report_lines.append(f"**测试模式**: {mode}\n")
    
    # 总体结果
    report_lines.append("## 📊 总体测试结果\n")
    report_lines.append("| 指标 | 数值 |")
    report_lines.append("|------|------|")
    report_lines.append(f"| 总测试用例数 | {total_cases} |")
    if mode == "API":
        report_lines.append(f"| API 调用成功 | {api_success} |")
    report_lines.append(f"| ✅ 整体通过 | {passed_cases} |")
    report_lines.append(f"| ❌ 整体失败 | {total_cases - passed_cases} |")
    report_lines.append(f"| 📈 整体通过率 | {passed_cases/total_cases*100:.1f}% |\n")
    
    # 按类别统计
    report_lines.append("## 📋 按类别统计\n")
    report_lines.append("| 类别 | 总数 | 通过 | 失败 | 通过率 |")
    report_lines.append("|------|------|------|------|--------|")
    for category, stats in category_stats.items():
        pass_rate = stats["passed"]/stats["total"]*100 if stats["total"] > 0 else 0
        report_lines.append(f"| {category} | {stats['total']} | {stats['passed']} | {stats['failed']} | {pass_rate:.1f}% |")
    report_lines.append("")
    
    # 详细结果
    report_lines.append("## 📝 详细测试结果\n")
    for result in results:
        status_emoji = "✅" if result.get("passed", False) else "❌"
        report_lines.append(f"### {status_emoji} {result['id']}: {result['name']}\n")
        report_lines.append(f"- **类别**: {result['category']}")
        report_lines.append(f"- **子类别**: {result['subcategory']}")
        report_lines.append(f"- **描述**: {result['description']}")
        report_lines.append(f"- **耗时**: {result['elapsed_time']:.2f} 秒\n")
        
        if not result.get("api_success", True):
            report_lines.append(f"**{mode} 错误**: {result.get('error', 'Unknown error')}\n")
        
        report_lines.append("#### 📨 请求与响应\n")
        report_lines.append(f"**👤 用户消息**: {result['user_message']}\n")
        report_lines.append(f"**🤖 AI 回复**: {result.get('ai_reply', '')}\n")
        
        if "checks" in result:
            report_lines.append("#### ✅ 检查详情\n")
            checks = result["checks"]
            for keyword in checks.get("expected_found", []):
                report_lines.append(f"- ✅ 包含预期关键词: {keyword}")
            for keyword in checks.get("expected_missing", []):
                report_lines.append(f"- ❌ 缺少预期关键词: {keyword}")
            for keyword in checks.get("unexpected_found", []):
                report_lines.append(f"- ❌ 包含不期望关键词: {keyword}")
            for keyword in checks.get("unexpected_not_found", []):
                report_lines.append(f"- ✅ 不包含不期望关键词: {keyword}")
            report_lines.append("")
        
        report_lines.append("---\n")
    
    # 时间统计
    report_lines.append(f"\n## ⏱️  时间统计\n")
    report_lines.append(f"- 总耗时: {end_time - start_time:.2f} 秒")
    report_lines.append(f"- 平均每用例: {(end_time - start_time)/total_cases:.2f} 秒\n")
    
    return "\n".join(report_lines)

# ========================================
# 主函数
# ========================================
def main():
    parser = argparse.ArgumentParser(description="Coze 平台工作流测试")
    parser.add_argument("--mode", choices=["api", "local"], default="local", 
                      help="测试模式: api (远程API) 或 local (本地运行)")
    parser.add_argument("--output", default="assets/Coze_API_完整测试报告.md", 
                      help="报告输出路径")
    
    args = parser.parse_args()
    mode = args.mode.upper()
    
    print("=" * 80)
    print(f"🚀 Coze 平台工作流 {mode} 完整测试开始")
    print("=" * 80)
    if mode == "API":
        print(f"API 地址: {COZE_API_URL}")
    print(f"工作流 ID: {WORKFLOW_ID}")
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # 创建输出目录
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # 执行测试
    results = []
    start_time = time.time()
    
    for category_group in TEST_CASES:
        category = category_group["category"]
        subcategory = category_group["subcategory"]
        cases = category_group["cases"]
        
        print(f"📋 测试场景: {category} - {subcategory}")
        print("-" * 80)
        
        for case in cases:
            print(f"\n🧪 执行测试: {case['id']} - {case['name']}")
            print(f"   描述: {case['description']}")
            print(f"   用户消息: {case['user_message']}")
            
            case_start = time.time()
            
            # 每个测试用例使用独立的 user_id，避免共享对话历史
            test_user_id = f"test_user_{case['id']}"
            
            # 执行测试
            if mode == "API":
                api_result = call_api(case["user_message"], user_id=test_user_id)
            else:
                api_result = run_local(case["user_message"], user_id=test_user_id)
            
            case_elapsed = time.time() - case_start
            
            # 解析结果
            result = {
                "id": case["id"],
                "name": case["name"],
                "category": category,
                "subcategory": subcategory,
                "description": case["description"],
                "user_message": case["user_message"],
                "elapsed_time": case_elapsed,
                "api_success": api_result["success"]
            }
            
            if api_result["success"]:
                ai_reply = api_result["data"].get("reply_content", "")
                result["ai_reply"] = ai_reply
                
                # 检查结果
                check_result_data = check_result(
                    ai_reply,
                    case["expected_keywords"],
                    case["unexpected_keywords"]
                )
                result["passed"] = check_result_data["passed"]
                result["checks"] = check_result_data["checks"]
                
                print(f"   {'✅' if result['passed'] else '❌'} 测试结果: {'通过' if result['passed'] else '失败'}")
                print(f"   ⏱️  耗时: {case_elapsed:.2f} 秒")
                
                checks = check_result_data["checks"]
                for keyword in checks["unexpected_not_found"]:
                    print(f"   ✅ 不包含不期望关键词: {keyword}")
                for keyword in checks["expected_missing"]:
                    print(f"   ❌ 缺少预期关键词: {keyword}")
                for keyword in checks["unexpected_found"]:
                    print(f"   ❌ 包含不期望关键词: {keyword}")
            else:
                result["passed"] = False
                result["error"] = api_result.get("error", "")
                print(f"   ❌ 测试结果: 失败")
                print(f"   ⏱️  耗时: {case_elapsed:.2f} 秒")
                print(f"   ❌ 错误: {result['error']}")
            
            results.append(result)
    
    end_time = time.time()
    
    # 生成报告
    print()
    print("=" * 80)
    print("📝 生成测试报告...")
    report_content = generate_markdown_report(results, start_time, end_time, mode)
    
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print(f"✅ 测试报告已保存到: {os.path.abspath(args.output)}")
    
    # 打印总结
    total_cases = len(results)
    passed_cases = sum(1 for r in results if r.get("passed", False))
    
    print()
    print("=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print(f"总测试用例数: {total_cases}")
    print(f"✅ 整体通过: {passed_cases}")
    print(f"❌ 整体失败: {total_cases - passed_cases}")
    print(f"📈 整体通过率: {passed_cases/total_cases*100:.1f}%")
    print("=" * 80)
    print()
    print(f"🎉 Coze {mode} 完整测试完成！")
    print(f"📖 查看完整报告: {os.path.abspath(args.output)}")

if __name__ == "__main__":
    main()
