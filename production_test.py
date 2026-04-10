#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境测试脚本 - 5轮真实测试
"""
import os
import sys
import json
import time
import requests
from datetime import datetime

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

def print_separator(title=""):
    """打印分隔线"""
    print("\n" + "=" * 80)
    if title:
        print(f"  {title}")
        print("=" * 80)

def call_coze_api(user_message: str, user_id: str):
    """调用 Coze API"""
    payload = {
        "user_message": user_message,
        "user_id": user_id
    }
    
    print(f"  [请求] POST {COZE_API_URL}")
    print(f"  [请求体] {json.dumps(payload, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            COZE_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"  [响应状态码] {response.status_code}")
        
        response.raise_for_status()
        
        result = response.json()
        print(f"  [响应数据] {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        return {
            "success": True,
            "status_code": response.status_code,
            "data": result
        }
    except Exception as e:
        print(f"  [错误] {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def main():
    print_separator("🚀 生产环境测试开始")
    print(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  工作流 ID: {WORKFLOW_ID}")
    print(f"  API 地址: {COZE_API_URL}")
    print(f"  测试用例数: {len(TEST_CASES)}")
    print("=" * 80)
    
    results = []
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print_separator(f"🧪 第 {i} 轮测试 - {test_case['id']}: {test_case['name']}")
        
        user_id = f"prod_test_{test_case['id']}"
        
        print(f"\n[测试用例信息]")
        print(f"  编号: {test_case['id']}")
        print(f"  名称: {test_case['name']}")
        print(f"  用户 ID: {user_id}")
        print(f"  输入: {test_case['user_message']}")
        
        print(f"\n[开始执行]")
        start_time = time.time()
        
        # 调用 Coze API
        result = call_coze_api(test_case['user_message'], user_id)
        
        elapsed_time = time.time() - start_time
        
        print(f"\n[测试结果]")
        print(f"  耗时: {elapsed_time:.2f} 秒")
        
        if result['success']:
            print(f"  状态: ✅ 成功")
            
            ai_reply = result['data'].get('reply_content', '')
            print(f"\n[AI 回复]")
            print(f"  {ai_reply}")
            
            results.append({
                "id": test_case['id'],
                "name": test_case['name'],
                "success": True,
                "user_message": test_case['user_message'],
                "ai_reply": ai_reply,
                "response": result['data'],
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
    print_separator("📊 生产环境测试总结")
    
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
    
    print_separator("🎉 生产环境测试完成")
    
    # 保存结果到文件
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "production_test_results.json")
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
