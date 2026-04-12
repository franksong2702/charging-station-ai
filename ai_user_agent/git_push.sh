#!/bin/bash

# AI 用户智能体 - GitHub 提交脚本
# 用于将代码提交到指定仓库的 dev 分支

set -e  # 遇到错误立即退出

echo "========================================"
echo "  AI 用户智能体 - GitHub 提交脚本"
echo "========================================"
echo ""

# 配置
REPO_URL="https://github.com/franksong2702/charging-station-ai.git"
BRANCH="dev"
TARGET_DIR="ai_user_agent"

# 检查是否在正确的目录
if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ 错误：未找到 $TARGET_DIR 目录"
    echo "   请在包含 $TARGET_DIR 目录的位置运行此脚本"
    exit 1
fi

echo "📋 配置信息："
echo "   仓库：$REPO_URL"
echo "   分支：$BRANCH"
echo "   目录：$TARGET_DIR"
echo ""

# 检查 Git 是否已初始化
cd "$TARGET_DIR"

if [ ! -d ".git" ]; then
    echo "📦 初始化 Git 仓库..."
    git init
    git remote add origin "$REPO_URL"
    echo "   ✓ Git 仓库已初始化"
else
    echo "✓ Git 仓库已存在"
fi

echo ""

# 检查当前状态
echo "📊 检查文件状态..."
git status --short
echo ""

# 添加所有文件
echo "➕ 添加文件到暂存区..."
git add .
echo "   ✓ 文件已添加"
echo ""

# 提交
echo "💾 提交更改..."
COMMIT_MSG="feat: 添加 AI 用户智能体用于测试充电桩客服系统

- 实现核心智能体逻辑 (agent.py)
- 提供 REST API 接口 (api.py)
- 配置 6 种测试场景 (scenarios.py)
- 支持多轮对话和会话管理
- 包含完整的文档和测试示例"

git commit -m "$COMMIT_MSG"
echo "   ✓ 提交完成"
echo ""

# 推送到远程仓库
echo "🚀 推送到远程仓库 (分支: $BRANCH)..."
echo ""

# 检查远程分支是否存在
if git ls-remote --heads origin "$BRANCH" | grep -q "$BRANCH"; then
    # 分支已存在，尝试推送
    echo "   分支已存在，尝试推送..."
    if git push origin "$BRANCH"; then
        echo "   ✓ 推送成功"
    else
        echo "   ⚠️  推送失败，可能需要拉取最新代码"
        echo "   请手动执行："
        echo "   cd $TARGET_DIR"
        echo "   git pull origin $BRANCH --rebase"
        echo "   git push origin $BRANCH"
        exit 1
    fi
else
    # 分支不存在，创建并推送
    echo "   分支不存在，创建新分支并推送..."
    git push -u origin "$BRANCH"
    echo "   ✓ 推送成功"
fi

echo ""
echo "========================================"
echo "  ✅ 提交完成！"
echo "========================================"
echo ""
echo "📊 提交信息："
echo "   仓库：$REPO_URL"
echo "   分支：$BRANCH"
echo "   目录：$TARGET_DIR"
echo ""
echo "🔗 查看代码："
echo "   https://github.com/franksong2702/charging-station-ai/tree/$BRANCH/$TARGET_DIR"
echo ""
echo "📝 下一步："
echo "   1. 在 GitHub 上查看提交的代码"
echo "   2. 安装依赖：pip install -r requirements.txt"
echo "   3. 启动服务：python api.py"
echo "   4. 访问 API 文档：http://localhost:8000/docs"
echo ""
