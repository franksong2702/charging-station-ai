"""
运行 Auto-Research 基准测试（简化版）
只跑 v1 版本的 10 个场景，不跑 5 轮迭代
"""
import sys
import os
import asyncio

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.auto_research_fallback import run_all_scenarios, generate_report

async def main():
    """主函数"""
    print("=" * 60)
    print("Auto-Research 基准测试（简化版）")
    print("=" * 60)
    
    # 只运行基准测试 (v1)
    print("\n--- 运行基准测试 (v1) ---")
    v1_result = await run_all_scenarios("v1")
    
    # 生成简化报告
    print("\n" + "=" * 60)
    print("基准测试结果")
    print("=" * 60)
    
    print(f"\n总场景数: {v1_result['total']}")
    print(f"通过: {v1_result['passed']}")
    print(f"失败: {v1_result['failed']}")
    print(f"通过率: {v1_result['pass_rate']:.1%}")
    
    print("\n场景详情:")
    print("-" * 60)
    
    for result in v1_result['results']:
        status = "✅" if result.get("success", False) else "❌"
        turns = result.get("turns", 0)
        case_created = "是" if result.get("case_created", False) else "否"
        print(f"{status} {result['scenario_name']} - {turns} 轮 - 工单创建: {case_created}")
        
        if not result.get("success", False):
            error = result.get("error", "未知错误")
            print(f"   错误: {error}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
