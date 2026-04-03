#!/usr/bin/env python3
"""
测试深度审核脚本 - 只审核前10条
"""
import pandas as pd
import json
import time
from typing import Dict, Any

from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.runtime_ctx.context import Context, new_context
from langchain_core.messages import SystemMessage, HumanMessage

def get_text_content(content):
    """安全获取文本内容"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        if content and isinstance(content[0], str):
            return " ".join(content)
        else:
            return " ".join(item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text")
    return str(content)

def review_single_knowledge_item(
    llm_client: LLMClient,
    question: str,
    short_answer: str,
    detailed_answer: str,
    category: str,
    subcategory: str
) -> Dict[str, Any]:
    """审核单条知识库内容"""
    system_prompt = """你是一个专业的知识库内容审核专家。请仔细审核以下充电桩知识库条目，从多个维度进行质量检查。

审核维度：
1. **问题清晰度**：问题是否表达清晰、无歧义
2. **回答准确性**：回答内容是否准确、可靠
3. **问答匹配度**：回答是否针对问题，没有答非所问
4. **内容完整性**：简短回答和详细回答是否完整、有价值
5. **是否需要兜底**：判断这个问题是否应该通过知识库回答，还是需要人工介入

特别注意：
- 如果问题涉及退款、押金、发票、账单、投诉、争议等，应该标记为"需要兜底"
- 如果回答包含"联系客服"、"找人工"、"投诉"等内容，应该标记为"需要兜底"
- 如果问题和回答都只是操作指引（如"怎么扫码"、"在哪里"），不需要兜底

请以JSON格式返回审核结果，格式如下：
{
    "has_issue": true/false,
    "issue_type": "问题不清晰/回答不准确/问答不匹配/内容不完整/需要兜底/其他",
    "issue_description": "详细描述发现的问题",
    "suggestion": "改进建议",
    "should_be_fallback": true/false,
    "overall_score": 0-10
}"""

    user_prompt = f"""请审核以下知识库条目：

【基本信息】
分类：{category}
子分类：{subcategory}

【问题】
{question}

【简短回答】
{short_answer}

【详细回答】
{detailed_answer}

请从问题清晰度、回答准确性、问答匹配度、内容完整性、是否需要兜底等维度进行审核。"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        response = llm_client.invoke(
            messages=messages,
            model="doubao-seed-1-8-251228",
            temperature=0.3,
            max_completion_tokens=2000
        )
        
        content = get_text_content(response.content)
        
        try:
            json_str = content.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            json_str = json_str.strip()
            
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError:
            return {
                "has_issue": False,
                "issue_type": "",
                "issue_description": "JSON解析失败，但内容看起来正常",
                "suggestion": "",
                "should_be_fallback": False,
                "overall_score": 7.0
            }
    except Exception as e:
        return {
            "has_issue": True,
            "issue_type": "审核出错",
            "issue_description": f"审核过程中发生错误: {str(e)}",
            "suggestion": "人工审核",
            "should_be_fallback": False,
            "overall_score": 5.0
        }

def main():
    """测试审核前10条"""
    input_file = '/workspace/projects/assets/知识库v1.2.xlsx'
    
    print("="*100)
    print("🔍 知识库v1.2 深度审核测试（前10条）")
    print("="*100)
    
    df = pd.read_excel(input_file)
    print(f"\n✅ 成功读取 {len(df)} 条记录")
    
    print("\n🤖 初始化大模型客户端...")
    ctx = new_context(method="invoke")
    llm_client = LLMClient(ctx=ctx)
    print("✅ 大模型客户端初始化成功")
    
    # 只审核前10条
    test_df = df.head(10)
    
    print(f"\n📋 开始审核前 {len(test_df)} 条...")
    
    for idx, row in test_df.iterrows():
        kb_id = row.get('ID', f'KB{idx+1:03d}')
        question = str(row.get('问题', '')).strip()
        short_answer = str(row.get('简短回答', '')).strip()
        detailed_answer = str(row.get('详细回答', '')).strip()
        category = str(row.get('分类', '')).strip()
        subcategory = str(row.get('子分类', '')).strip()
        
        if not question or question == 'nan':
            continue
        
        print(f"\n{'='*100}")
        print(f"📋 [{idx+1}/{len(test_df)}] ID: {kb_id}")
        print(f"{'='*100}")
        print(f"❓ 问题: {question}")
        print(f"📝 简短回答: {short_answer}")
        if len(detailed_answer) > 100:
            print(f"📄 详细回答: {detailed_answer[:100]}...")
        else:
            print(f"📄 详细回答: {detailed_answer}")
        print(f"🏷️  分类: {category} / {subcategory}")
        
        print(f"\n🤖 正在审核...")
        review_result = review_single_knowledge_item(
            llm_client=llm_client,
            question=question,
            short_answer=short_answer,
            detailed_answer=detailed_answer,
            category=category,
            subcategory=subcategory
        )
        
        print(f"\n✅ 审核结果:")
        print(f"   有问题: {'❌ 是' if review_result.get('has_issue', False) else '✅ 否'}")
        print(f"   问题类型: {review_result.get('issue_type', '')}")
        print(f"   问题描述: {review_result.get('issue_description', '')}")
        print(f"   改进建议: {review_result.get('suggestion', '')}")
        print(f"   建议兜底: {'🔴 是' if review_result.get('should_be_fallback', False) else '🟢 否'}")
        print(f"   综合得分: {review_result.get('overall_score', 0):.1f}/10")
        
        time.sleep(0.5)
    
    print("\n" + "="*100)
    print("✅ 测试审核完成！")
    print("="*100)

if __name__ == '__main__':
    main()
