#!/usr/bin/env python3
"""
简单测试：看看意图识别返回了什么
"""
import os
import sys

# 设置项目路径
project_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
src_path = os.path.join(project_path, "src")
sys.path.insert(0, src_path)
sys.path.insert(0, project_path)

# 导入工作流
from src.graphs.graph import main_graph

print("="*80)
print("测试意图识别")
print("="*80)

test_messages = [
    "什么垃圾服务！充电桩充不进去电，我都等了半小时了！",
    "我要投诉",
    "垃圾服务",
    "充不进去电怎么办？"
]

for msg in test_messages:
    print(f"\n👤 用户消息: {msg}")
    try:
        result = main_graph.invoke({
            "user_message": msg,
            "user_id": "test_intent_123"
        })
        print(f"🤖 AI 回复: {result.get('reply_content', '')[:100]}...")
        
        # 看看state里有没有intent（如果有的话）
        if 'intent' in result:
            print(f"🎯 识别的意图: {result.get('intent', '')}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")

print("\n" + "="*80)
print("测试完成")
print("="*80)
