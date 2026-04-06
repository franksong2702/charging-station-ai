import pandas as pd

# 读取知识库文件
df = pd.read_excel('/workspace/projects/assets/知识库v1.3.xlsx')

print("=" * 120)
print(f"知识库 v1.3 - 完整数据列表 (共 {len(df)} 条)")
print("=" * 120)

for idx, row in df.iterrows():
    print(f"\n【{idx+1}】ID: {row['ID']}")
    print(f"    分类: {row['分类']} | 子分类: {row['子分类']}")
    print(f"    问题: {row['问题']}")
    if pd.notna(row['简短回答']) and str(row['简短回答']).strip():
        short_ans = str(row['简短回答'])[:50] + "..." if len(str(row['简短回答'])) > 50 else str(row['简短回答'])
        print(f"    简短回答: {short_ans}")
