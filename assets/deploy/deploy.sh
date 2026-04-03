#!/bin/bash
# ================================
# 腾讯云函数 - 一键部署脚本
# 版本: v1.0
# ================================

set -e

echo "=========================================="
echo "   充电桩智能客服 - 腾讯云函数部署"
echo "=========================================="
echo ""

# ==================== 颜色定义 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==================== 检查依赖 ====================
echo -e "${YELLOW}[1/6] 检查依赖...${NC}"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}错误: 未安装 Node.js${NC}"
    echo "请先安装 Node.js: https://nodejs.org/"
    exit 1
fi
echo -e "  ✓ Node.js $(node -v)"

# 检查 npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}错误: 未安装 npm${NC}"
    exit 1
fi
echo -e "  ✓ npm $(npm -v)"

# 检查 Serverless Framework
if ! command -v serverless &> /dev/null; then
    echo -e "${YELLOW}  Serverless Framework 未安装，正在安装...${NC}"
    npm install -g serverless
fi
echo -e "  ✓ Serverless Framework $(serverless -v | head -1)"

# 安装腾讯云插件
if ! npm list @serverless/tencent-component &> /dev/null; then
    echo -e "${YELLOW}  安装腾讯云组件...${NC}"
    npm install @serverless/tencent-component --save-dev
fi

echo ""

# ==================== 配置检查 ====================
echo -e "${YELLOW}[2/6] 检查配置...${NC}"

# 检查必要文件
if [ ! -f "cloud_function.py" ]; then
    echo -e "${RED}错误: 找不到 cloud_function.py${NC}"
    exit 1
fi
echo -e "  ✓ cloud_function.py 存在"

if [ ! -f "serverless.yml" ]; then
    echo -e "${RED}错误: 找不到 serverless.yml${NC}"
    exit 1
fi
echo -e "  ✓ serverless.yml 存在"

echo ""

# ==================== 环境变量配置 ====================
echo -e "${YELLOW}[3/6] 环境变量配置${NC}"
echo ""
echo "请确保已设置以下环境变量（或直接在 serverless.yml 中配置）:"
echo "  - TENCENT_SECRET_ID: 腾讯云API密钥ID"
echo "  - TENCENT_SECRET_KEY: 腾讯云API密钥Key"
echo ""

# 检查环境变量
if [ -z "$TENCENT_SECRET_ID" ] || [ -z "$TENCENT_SECRET_KEY" ]; then
    echo -e "${YELLOW}未设置 TENCENT_SECRET_ID 或 TENCENT_SECRET_KEY${NC}"
    echo ""
    echo "请选择配置方式:"
    echo "  1) 设置环境变量"
    echo "  2) 使用临时密钥（本次部署有效）"
    echo "  3) 跳过检查（已在 serverless.yml 配置）"
    read -p "请选择 [1-3]: " choice
    
    case $choice in
        1)
            echo "请手动设置环境变量后重新运行:"
            echo "  export TENCENT_SECRET_ID=your_secret_id"
            echo "  export TENCENT_SECRET_KEY=your_secret_key"
            exit 0
            ;;
        2)
            echo ""
            read -p "请输入腾讯云 Secret ID: " temp_id
            read -p "请输入腾讯云 Secret Key: " temp_key
            export TENCENT_SECRET_ID="$temp_id"
            export TENCENT_SECRET_KEY="$temp_key"
            ;;
        3)
            echo "继续部署..."
            ;;
        *)
            echo -e "${RED}无效选择${NC}"
            exit 1
            ;;
    esac
fi

echo ""

# ==================== 配置参数 ====================
echo -e "${YELLOW}[4/6] 配置参数${NC}"
echo ""

# 询问AI工作流API地址
read -p "请输入AI工作流API地址 (例如: http://1.2.3.4:5000/run): " api_url
if [ -z "$api_url" ]; then
    echo -e "${RED}错误: API地址不能为空${NC}"
    exit 1
fi

# 询问企业微信配置
echo ""
echo "企业微信配置（可选，稍后可在控制台配置）:"
read -p "企业ID (WECHAT_CORP_ID): " corp_id
read -p "应用AgentId (WECHAT_AGENT_ID): " agent_id
read -p "应用Secret (WECHAT_SECRET): " secret
read -p "应用Token (WECHAT_TOKEN): " token

# 更新 serverless.yml 中的环境变量
if [ "$corp_id" ] || [ "$api_url" ]; then
    echo -e "${GREEN}更新配置文件...${NC}"
    
    # 使用 Python 更新 YAML 文件（如果有 pyyaml）
    if python3 -c "import yaml" 2>/dev/null; then
        python3 << EOF
import yaml

with open('serverless.yml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

env_vars = config['provider']['environment']['variables']
env_vars['AI_WORKFLOW_API_URL'] = '$api_url'
if '$corp_id':
    env_vars['WECHAT_CORP_ID'] = '$corp_id'
if '$agent_id':
    env_vars['WECHAT_AGENT_ID'] = '$agent_id'
if '$secret':
    env_vars['WECHAT_SECRET'] = '$secret'
if '$token':
    env_vars['WECHAT_TOKEN'] = '$token'

with open('serverless.yml', 'w', encoding='utf-8') as f:
    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
EOF
        echo -e "  ✓ 配置已更新"
    else
        echo -e "${YELLOW}  未安装 pyyaml，请手动更新 serverless.yml${NC}"
    fi
fi

echo ""

# ==================== 部署 ====================
echo -e "${YELLOW}[5/6] 开始部署...${NC}"
echo ""

# 执行部署
serverless deploy

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}[6/6] 部署成功！${NC}"
    echo ""
    echo "=========================================="
    echo "   后续步骤"
    echo "=========================================="
    echo ""
    echo "1. 获取云函数URL:"
    echo "   部署输出中会显示 API Gateway 的地址"
    echo ""
    echo "2. 配置企业微信回调:"
    echo "   登录企业微信管理后台 -> 应用管理 -> 自建应用"
    echo "   设置API接收消息的URL为: https://your-api-url/wechat"
    echo ""
    echo "3. 设置Token和EncodingAESKey:"
    echo "   在企业微信后台设置与 serverless.yml 中相同的值"
    echo ""
    echo "4. 测试调用:"
    echo "   curl -X POST https://your-api-url/test \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"user_message\":\"充电枪拔不出来\"}'"
    echo ""
    echo "=========================================="
else
    echo ""
    echo -e "${RED}部署失败！${NC}"
    echo "请检查错误信息并重试"
    exit 1
fi
