#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
透明实时测试 - 每一步都打印真实日志
"""
import os
import sys
import json
import time
import requests
from datetime import datetime

# 添加项目根目录到 PYTHONPATH
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, PROJECT_ROOT)

COZE_API_URL = "https://wp5bsz5qfm.coze.site/run"
WORKFLOW_ID = "7619179949030801458"

# 5个测试用例
TEST_CASES = [
    {
        "id": "TC-001",
        "name": "使用指导 - 特斯拉充电桩怎么扫码",
        "user_message": "特斯拉充电桩怎么扫码？"
    },
    {
        "id": "TC-002",
        "name": "故障处理 - 充不进去电怎么办",
        "user_message": "充不进去电怎么办？"
    },
    {
        "id": "TC-003",
        "name": "协商处理 - 我要退款",
        "user_message": "我要退款"
    },
    {
        "id": "TC-004",
        "name": "投诉兜底 - 我要投诉",
        "user_message": "我要投诉"
    },
    {
        "id": "TC-005",
        "name": "评价反馈 - 谢谢",
        "user_message": "谢谢"
    }
]

def run_local_test(user_message: str, user_id: str):
    """本地运行模式"""
    from src.main import service
    import asyncio
    
    print("  [步骤 2/3] 正在调用本地工作流...")
    
    try:
        result = asyncio.run(service.run({
            "user_message": user_message,
            "user_id": user_id
        }))
        
        print(f"  [步骤 3/3] 本地工作流调用成功！")
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        import traceback
        print(f"  [错误] 本地工作流调用失败！")
        print(f"  [错误详情] {str(e)}")
        print(f"  [堆栈跟踪] {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }

def print_separator(title=""):
    """打印分隔线"""
    print("\n" + "=" * 80)
    if title:
        print(f"  {title}")
        print("=" * 80)

def main():
    print_separator("🚀 开始透明实时测试")
    print(f"  测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  工作流 ID: {WORKFLOW_ID}")
    print(f"  测试模式: LOCAL (本地运行)")
    print(f"  测试用例数: {len(TEST_CASES)}")
    print("=" * 80)
    
    results = []
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print_separator(f"🧪 第 {i} 轮测试 - {test_case['id']}: {test_case['name']}")
        
        user_id = f"test_transparent_{test_case['id']}"
        
        print(f"\n[测试用例信息]")
        print(f"  ID: {test_case['id']}")
        print(f"  名称: {test_case['name']}")
        print(f"  用户 ID: {user_id}")
        print(f"  用户消息: {test_case['user_message']}")
        
        print(f"\n[开始执行]")
        start_time = time.time()
        
        # 本地运行测试
        result = run_local_test(test_case['user_message'], user_id)
        
        elapsed_time = time.time() - start_time
        
        # 打印结果
        print(f"\n[测试结果]")
        print(f"  耗时: {elapsed_time:.2f} 秒")
        
        if result['success']:
            print(f"  状态: ✅ 成功")
            print(f"\n[响应数据]")
            print(json.dumps(result['data'], ensure_ascii=False, indent=2))
            
            ai_reply = result['data'].get('reply_content', '')
            print(f"\n[AI 回复]")
            print(f"  {ai_reply}")
            
            results.append({
                "id": test_case['id'],
                "name": test_case['name'],
                "success": True,
                "user_message": test_case['user_message'],
                "ai_reply": ai_reply,
                "elapsed_time": elapsed_time
            })
        else:
            print(f"  状态: ❌ 失败")
            print(f"  错误: {result.get('error', 'Unknown error')}")
            
            results.append({
                "id": test_case['id'],
                "name": test_case['name'],
                "success": False,
                "user_message": test_case['user_message'],
                "error": result.get('error', ''),
                "elapsed_time": elapsed_time
            })
    
    # 总结
    print_separator("📊 测试总结")
    
    total = len(results)
    passed = sum(1 for r in results if r['success'])
    failed = total - passed
    
    print(f"\n  总测试用例数: {total}")
    print(f"  ✅ 通过: {passed}")
    print(f"  ❌ 失败: {failed}")
    print(f"  📈 通过率: {passed/total*100:.1f}%")
    
    print(f"\n[详细结果]")
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"  {status} {result['id']}: {result['name']} ({result['elapsed_time']:.2f}s)")
    
    print_separator("🎉 透明实时测试完成")
    
    # 保存结果到文件
    output_file = os.path.join(PROJECT_ROOT, "assets", "transparent_test_results.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_cases": total,
            "passed": passed,
            "failed": failed,
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n  结果已保存到: {output_file}")

if __name__ == "__main__":
    main()
