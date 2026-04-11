#!/usr/bin/env python3
"""
生成工作流整体图
使用 LangGraph 的绘图功能生成工作流图并保存为图片
"""
import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from graphs.graph import main_graph

def generate_workflow_image():
    """生成工作流图并保存"""
    print("正在生成工作流图...")
    
    # 获取图对象
    graph = main_graph.get_graph()
    
    # 生成 Mermaid 格式的 PNG 图片
    try:
        # 生成图片
        image_bytes = graph.draw_mermaid_png()
        
        # 保存图片
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'workflow_diagram.png')
        
        # 确保 assets 目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 写入文件
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
        
        print(f"✅ 工作流图已成功生成并保存到: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ 生成工作流图时出错: {e}")
        # 降级方案：生成 Mermaid 文本
        try:
            mermaid_text = graph.draw_mermaid()
            mermaid_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'workflow_diagram.mmd')
            with open(mermaid_path, 'w', encoding='utf-8') as f:
                f.write(mermaid_text)
            print(f"已保存 Mermaid 文本到: {mermaid_path}")
            return mermaid_path
        except Exception as e2:
            print(f"保存 Mermaid 文本也失败: {e2}")
            return None

if __name__ == "__main__":
    generate_workflow_image()
