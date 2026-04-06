import pandas as pd

# 读取知识库文件
df = pd.read_excel('/workspace/projects/assets/知识库v1.3.xlsx')

print(f"总数据条数: {len(df)}")
print(f"\n列名: {df.columns.tolist()}")
print(f"\n前5条数据预览:")
print(df.head())
print(f"\n数据类型:")
print(df.dtypes)
