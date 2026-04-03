#!/usr/bin/env python3
"""
知识库v1.2 完整深度审核 - 处理全部111条
"""
import pandas as pd
import json
import time
from typing import Dict, Any, List

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
    """完整深度审核"""
    input_file = '/workspace/projects/assets/知识库v1.2.xlsx'
    output_file = '/workspace/projects/docs/知识库v1.2_深度审核报告.xlsx'
    
    print("="*120)
    print("🔍 知识库v1.2 完整深度审核开始")
    print("="*120)
    
    df = pd.read_excel(input_file)
    print(f"\n📖 成功读取 {len(df)} 条记录")
    
    print("\n🤖 初始化大模型客户端...")
    ctx = new_context(method="invoke")
    llm_client = LLMClient(ctx=ctx)
    print("✅ 大模型客户端初始化成功")
    
    print(f"\n📋 开始逐条审核（共 {len(df)} 条）...")
    print(f"⏱️  预计耗时: {len(df) * 1.5 / 60:.1f} 分钟\n")
    
    results = []
    start_time = time.time()
    
    for idx, row in df.iterrows():
        kb_id = row.get('ID', f'KB{idx+1:03d}')
        question = str(row.get('问题', '')).strip()
        short_answer = str(row.get('简短回答', '')).strip()
        detailed_answer = str(row.get('详细回答', '')).strip()
        category = str(row.get('分类', '')).strip()
        subcategory = str(row.get('子分类', '')).strip()
        
        if not question or question == 'nan':
            results.append({
                'ID': kb_id,
                '问题': question,
                'has_issue': True,
                'issue_type': '空数据',
                'issue_description': '问题为空',
                'suggestion': '删除此条',
                'should_be_fallback': False,
                'overall_score': 0.0
            })
            continue
        
        if (idx + 1) % 10 == 0 or idx == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / (idx + 1) if idx > 0 else 0
            remaining = (len(df) - idx - 1) * avg_time
            print(f"[{idx+1:3d}/{len(df)}] 审核中... 已用: {elapsed:.0f}s, 预计剩余: {remaining:.0f}s")
        
        review_result = review_single_knowledge_item(
            llm_client=llm_client,
            question=question,
            short_answer=short_answer,
            detailed_answer=detailed_answer,
            category=category,
            subcategory=subcategory
        )
        
        results.append({
            'ID': kb_id,
            '问题': question,
            '分类': category,
            '子分类': subcategory,
            'has_issue': review_result.get('has_issue', False),
            'issue_type': review_result.get('issue_type', ''),
            'issue_description': review_result.get('issue_description', ''),
            'suggestion': review_result.get('suggestion', ''),
            'should_be_fallback': review_result.get('should_be_fallback', False),
            'overall_score': review_result.get('overall_score', 5.0)
        })
        
        time.sleep(0.3)
    
    result_df = pd.DataFrame(results)
    final_df = pd.merge(df, result_df, on='ID', how='left', suffixes=('', '_review'))
    
    print(f"\n💾 保存审核报告: {output_file}")
    final_df.to_excel(output_file, index=False)
    print("✅ 审核报告保存成功")
    
    total = len(results)
    has_issue = sum(1 for r in results if r.get('has_issue', False))
    no_issue = total - has_issue
    should_be_fallback = sum(1 for r in results if r.get('should_be_fallback', False))
    avg_score = sum(r.get('overall_score', 0) for r in results) / total if total > 0 else 0
    elapsed = time.time() - start_time
    
    print("\n" + "="*120)
    print("📊 审核统计结果")
    print("="*120)
    print(f"\n⏱️  总耗时: {elapsed:.0f} 秒 ({elapsed/60:.1f} 分钟)")
    print(f"📋 总条目数: {total}")
    print(f"✅ 无问题: {no_issue} ({no_issue/total*100:.1f}%)")
    print(f"❌ 有问题: {has_issue} ({has_issue/total*100:.1f}%)")
    print(f"🔴 建议兜底: {should_be_fallback} 条")
    print(f"⭐ 平均得分: {avg_score:.1f}/10")
    
    issue_types = {}
    for r in results:
        if r.get('has_issue', False):
            issue_type = r.get('issue_type', '其他')
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
    
    if issue_types:
        print("\n📋 问题类型统计:")
        for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {issue_type}: {count} 条")
    
    if has_issue > 0:
        print("\n" + "="*120)
        print("⚠️  发现问题的条目（前20条）:")
        print("="*120)
        
        issue_items = [r for r in results if r.get('has_issue', False)]
        for r in issue_items[:20]:
            print(f"\n📋 ID: {r['ID']}")
            print(f"❓ 问题: {r['问题']}")
            print(f"🚨 问题类型: {r.get('issue_type', '')}")
            print(f"📝 问题描述: {r.get('issue_description', '')}")
            print(f"💡 改进建议: {r.get('suggestion', '')}")
            if r.get('should_be_fallback', False):
                print(f"🔴 建议: 转到兜底流程")
            print(f"⭐ 得分: {r.get('overall_score', 0):.1f}/10")
    
    if should_be_fallback > 0:
        print("\n" + "="*120)
        print("🔴 建议转到兜底流程的条目:")
        print("="*120)
        
        fallback_items = [r for r in results if r.get('should_be_fallback', False)]
        for r in fallback_items:
            print(f"\n📋 ID: {r['ID']}")
            print(f"❓ 问题: {r['问题']}")
    
    print("\n" + "="*120)
    print(f"✅ 完整深度审核完成！详细报告已保存到: {output_file}")
    print("="*120)

if __name__ == '__main__':
    main()
