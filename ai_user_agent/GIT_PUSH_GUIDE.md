# GitHub 提交指南

## 📦 快速提交

### 方式一：使用自动脚本（推荐）

```bash
cd /workspace/projects
cd ai_user_agent
./git_push.sh
```

脚本会自动完成：
- ✓ 初始化 Git 仓库（如果需要）
- ✓ 添加所有文件到暂存区
- ✓ 创建提交
- ✓ 推送到远程仓库的 dev 分支

### 方式二：手动提交

```bash
# 1. 进入项目目录
cd /workspace/projects/ai_user_agent

# 2. 初始化 Git 仓库（如果尚未初始化）
git init

# 3. 添加远程仓库
git remote add origin https://github.com/franksong2702/charging-station-ai.git

# 4. 添加所有文件
git add .

# 5. 创建提交
git commit -m "feat: 添加 AI 用户智能体用于测试充电桩客服系统

- 实现核心智能体逻辑 (agent.py)
- 提供 REST API 接口 (api.py)
- 配置 6 种测试场景 (scenarios.py)
- 支持多轮对话和会话管理
- 包含完整的文档和测试示例"

# 6. 创建 dev 分支（如果不存在）
git checkout -b dev

# 7. 推送到远程仓库
git push -u origin dev
```

## 🔄 后续更新

当代码有更新时，再次提交：

```bash
cd /workspace/projects/ai_user_agent
git add .
git commit -m "fix: 修复 xxx 问题"
git push origin dev
```

## 📂 项目结构

提交后的文件结构：

```
charging-station-ai/
└── ai_user_agent/
    ├── agent.py              # 核心智能体逻辑
    ├── api.py                # REST API 接口
    ├── scenarios.py          # 6 种测试场景配置
    ├── config.json           # 模型配置
    ├── requirements.txt      # Python 依赖
    ├── README.md             # 详细使用文档
    └── git_push.sh           # Git 提交脚本
```

## 🔍 提交信息

- **仓库**：https://github.com/franksong2702/charging-station-ai
- **分支**：dev
- **目录**：ai_user_agent
- **提交信息**：feat: 添加 AI 用户智能体用于测试充电桩客服系统

## ⚠️ 注意事项

1. **首次提交**：如果 dev 分支不存在，脚本会自动创建
2. **权限问题**：如果推送失败，请检查 GitHub 仓库访问权限
3. **冲突处理**：如果远程分支有更新，需要先拉取再推送

## 📝 查看提交

提交成功后，可以在浏览器查看：

https://github.com/franksong2702/charging-station-ai/tree/dev/ai_user_agent

## 🚀 后续使用

1. **克隆仓库**（在本地使用）：
   ```bash
   git clone -b dev https://github.com/franksong2702/charging-station-ai.git
   cd charging-station-ai/ai_user_agent
   ```

2. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

3. **启动服务**：
   ```bash
   python api.py
   ```

4. **访问 API 文档**：
   ```
   http://localhost:8000/docs
   ```
