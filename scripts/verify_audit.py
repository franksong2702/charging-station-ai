#!/usr/bin/env python3
"""
验证审核结果文件
"""
import pandas as pd

def main():
    file_path = '/workspace/projects/assets/知识库v1.1_带审核结果.xlsx'
    
    df = pd.read_excel(file_path)
    
    print("="*100)
    print("✅ 新文件验证成功！")
    print("="*100)
    print(f"\n📊 总行数: {len(df)}")
    print(f"\n📋 列名: {list(df.columns)}")
    
    print("\n" + "="*100)
    print("📄 前10条数据预览:")
    print("="*100)
    
    # 显示前10条，只显示关键列
    preview_cols = ['审核标识', '审核分类', '优先级', '处理建议', '问题', '审核原因']
    print(df[preview_cols].head(10).to_string())
    
    print("\n" + "="*100)
    print("🔴 所有兜底性内容（不应该放在知识库中）:")
    print("="*100)
    
    fallback_df = df[df['审核分类'].str.contains('兜底', na=False)]
    for idx, row in fallback_df.iterrows():
        print(f"\n{row['审核标识']} ID: {row.get('ID', 'N/A')}")
        print(f"   问题: {row['问题']}")
        print(f"   建议: {row['处理建议']}")
        print(f"   原因: {row['审核原因']}")
    
    print("\n" + "="*100)
    print("🟡 需要人工判断的内容（前10条）:")
    print("="*100)
    
    manual_df = df[df['审核分类'].str.contains('需要人工', na=False)]
    for idx, row in manual_df.head(10).iterrows():
        print(f"\n{row['审核标识']} ID: {row.get('ID', 'N/A')}")
        print(f"   问题: {row['问题']}")
        print(f"   建议: {row['处理建议']}")
        print(f"   原因: {row['审核原因']}")
    
    print(f"\n\n✅ 文件已生成: {file_path}")
    print("   你可以把这个Excel文件发给客户了！")

if __name__ == '__main__':
    main()
