import os
import sys

# 设置 PYTHONPATH
sys.path.insert(0, os.getenv("COZE_WORKSPACE_PATH"))
sys.path.insert(0, os.path.join(os.getenv("COZE_WORKSPACE_PATH"), "src"))

from graphs.graph import main_graph
from graphs.state import GraphInput


def test_global_state():
    """测试 GlobalState 的变化"""
    print("=== 测试 GlobalState ===")
    
    # 第一轮对话
    print("\n--- 第一轮对话 ---")
    input1 = GraphInput(
        user_message="我要投诉，昨天在徐汇滨江充电站",
        user_id="test_user_state1"
    )
    result1 = main_graph.invoke(input1.model_dump())
    print(f"第一轮结果 reply_content: {result1.get('reply_content', '')}")
    print(f"第一轮结果 fallback_phase: {result1.get('fallback_phase', '')}")
    print(f"第一轮结果 problem_summary: {result1.get('problem_summary', '')}")
    print(f"第一轮结果 entry_problem: {result1.get('entry_problem', '')}")
    
    # 打印所有 keys
    print(f"第一轮结果所有 keys: {list(result1.keys())}")


if __name__ == "__main__":
    test_global_state()