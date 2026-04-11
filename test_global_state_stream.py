import os
import sys

# 设置 PYTHONPATH
sys.path.insert(0, os.getenv("COZE_WORKSPACE_PATH"))
sys.path.insert(0, os.path.join(os.getenv("COZE_WORKSPACE_PATH"), "src"))

from graphs.graph import main_graph
from graphs.state import GraphInput, GlobalState


def test_global_state_with_stream():
    """测试 GlobalState 的变化，使用 stream 方法"""
    print("=== 测试 GlobalState（使用 stream）===")
    
    # 第一轮对话
    print("\n--- 第一轮对话 ---")
    input1 = GraphInput(
        user_message="我要投诉，昨天在徐汇滨江充电站",
        user_id="test_user_state_stream1"
    )
    
    # 使用 stream 方法，打印每一步的状态
    for event in main_graph.stream(input1.model_dump(), stream_mode="updates"):
        print(f"\n收到事件: {event}")
        for node_name, node_output in event.items():
            print(f"节点 {node_name} 输出:")
            print(f"  内容: {node_output}")
            print(f"  字段: {list(node_output.keys())}")
    
    print("\n--- 第一轮对话结束 ---")


if __name__ == "__main__":
    test_global_state_with_stream()