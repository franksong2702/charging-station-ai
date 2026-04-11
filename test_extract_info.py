import os
import json
from langchain_core.messages import HumanMessage
from tools.llm import create_llm_client
from coze_coding_utils.runtime_ctx.context import Context

def test_extract_info():
    # 模拟上下文
    ctx = Context()
    
    # 创建 LLM 客户端
    llm_client = create_llm_client(ctx)
    
    # 测试用户消息
    user_message = "手机号13812345678 车牌沪A12345"
    
    # 提示词
    prompt = f"""请从用户消息中提取以下信息，并以JSON格式返回：

1. phone: 用户提供的手机号（如果有）
2. license_plate: 用户提供的车牌号（如果有）
3. problem: 用户描述的问题（如果有）
4. time: 用户提到的时间（如果有，例如"今天早上"、"3点"等）
5. location: 用户提到的地点（如果有，例如"XX充电站"、"家附近"等）

用户消息："{user_message}"

示例输出1（有手机号、车牌号、问题）：
{{
    "phone": "13812345678",
    "license_plate": "沪A12345",
    "problem": "充电桩充不上电",
    "time": "",
    "location": ""
}}

示例输出2（只有问题）：
{{
    "phone": "",
    "license_plate": "",
    "problem": "充电桩坏了",
    "time": "今天下午",
    "location": "万达充电站"
}}

示例输出3（语音输入分段）：
用户说"手机号139。16425678。车牌号。沪a Dr 3509。"
{{
    "phone": "13916425678",
    "license_plate": "沪ADR3509",
    "problem": "",
    "time": "",
    "location": ""
}}

注意事项：
1. 手机号提取：只提取数字，忽略空格和标点
2. 车牌号提取：去除空格，字母统一大写
3. 问题提取：完整保留用户问题描述
4. 如果没有某项信息，返回空字符串""
5. 只返回JSON，不要有其他文字
"""
    
    # 调用 LLM
    print(f"正在调用 LLM 提取信息...")
    print(f"用户消息: {user_message}")
    
    try:
        response = llm_client.invoke([HumanMessage(content=prompt)])
        response_text = response.content.strip()
        print(f"\nLLM 返回: {response_text}")
        
        # 解析 JSON
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        try:
            result = json.loads(response_text.strip())
            print(f"\n解析结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError as e:
            print(f"\nJSON 解析失败: {e}")
            
    except Exception as e:
        print(f"\n调用 LLM 失败: {e}")

if __name__ == "__main__":
    test_extract_info()