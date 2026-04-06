import pandas as pd

# 读取知识库文件
df = pd.read_excel('/workspace/projects/assets/知识库v1.3.xlsx')

# 只保留有效数据（前98条）
df_valid = df.iloc[:98].copy()

print("=" * 120)
print(f"知识库 v1.3 - 有效数据分析（共 {len(df_valid)} 条）")
print("=" * 120)

print(f"\n📊 分类统计:")
print(df_valid['分类'].value_counts().to_string())

print(f"\n📋 完整问题列表:")
print("-" * 120)

for idx, row in df_valid.iterrows():
    print(f"\n【{idx+1}】{row['问题']}")
    print(f"    分类: {row['分类']} | 子分类: {row['子分类']}")
    if pd.notna(row['简短回答']) and str(row['简短回答']).strip():
        short_ans = str(row['简短回答'])[:60] + "..." if len(str(row['简短回答'])) > 60 else str(row['简短回答'])
        print(f"    简短回答: {short_ans}")
