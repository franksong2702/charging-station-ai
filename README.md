# 充电桩智能客服工作流

基于 LangGraph 的充电桩智能客服系统，支持文字和语音输入，支持多轮对话和评价机制。

## 功能特性

- ✅ **意图识别**：自动识别用户问题类型（使用指导/故障处理/投诉兜底/评价反馈）
- ✅ **知识库问答**：基于知识库回答充电桩相关问题
- ✅ **多轮对话**：通过 user_id 支持对话上下文记忆
- ✅ **语音输入**：支持语音消息，自动 ASR 转文字
- ✅ **评价机制**：知识库问答后收集用户反馈
- ✅ **投诉处理**：收集用户信息并发送邮件通知客服
- ✅ **对话记录**：所有对话自动保存到数据库

## 快速开始

### 本地运行

```bash
# 运行工作流
bash scripts/local_run.sh -m flow

# 运行单个节点
bash scripts/local_run.sh -m node -n node_name

# 启动 HTTP 服务
bash scripts/http_run.sh -m http -p 5000
```

### AI User Agent 集成测试

```bash
# 先配置环境变量（参考 .env.example）
export COZE_API_TOKEN="..."
export AI_USER_AGENT_TOKEN="..."
export COZE_WORKFLOW_PROJECT_ID="7619179949030801458"

# 可选：覆盖默认地址
export COZE_WORKFLOW_API="https://wp5bsz5qfm.coze.site/run"
export AI_USER_AGENT_API="https://jr9h465hzr.coze.site/stream_run"
export AI_USER_AGENT_PROJECT_ID="7627835614766841865"

# 运行集成测试
python src/tests/ai_user_integration_test.py --max-turns 8
```

测试报告会输出到 `/tmp/ai_user_integration_test_*.md`。

安全保护：
- 脚本默认拒绝对线上客服正式环境执行测试（`https://wxvghzzb8f.coze.site/run`）。
- 若必须覆盖，需显式设置：`export ALLOW_PROD_TEST=true`。

### 输入格式

```json
{
  "user_message": "充电桩怎么使用",
  "voice_url": "语音URL（可选）",
  "user_id": "用户ID（可选，用于多轮对话）"
}
```

### 输出格式

```json
{
  "reply_content": "AI客服的回复内容"
}
```

## 架构说明

### 工作流流程

```
用户输入 → 加载历史 → 意图识别 → 分支处理 → 保存记录 → 返回回复
                           ↓
              ┌────────────┼────────────┐
              ↓            ↓            ↓
         知识库问答    投诉处理    评价反馈
              ↓            ↓            ↓
         保存历史    发送邮件    记录评价
              ↓            ↓            ↓
         保存记录 ← ────────┴────────────┘
```

### 节点说明

| 节点 | 功能 |
|-----|------|
| load_history | 根据 user_id 加载对话历史 |
| intent_recognition | 识别用户意图 |
| knowledge_qa | 知识库问答 |
| save_history | 保存对话历史（用于多轮对话） |
| save_record | 保存对话记录（用于分析） |
| feedback | 处理用户评价 |
| info_collection | 收集投诉信息 |
| email_sending | 发送邮件通知 |

### 数据库表

| 表名 | 用途 |
|-----|------|
| conversation_history | 对话历史（用于多轮对话上下文） |
| dialog_records | 对话记录（用于后续分析） |

## 配置说明

### 邮件配置（投诉功能）

在 Coze 平台添加邮件集成（integration-email-imap-smtp），配置：

| 配置项 | 说明 |
|-------|------|
| smtp_server | SMTP 服务器地址 |
| smtp_port | SMTP 端口（SSL 通常为 465） |
| account | 发件邮箱账号 |
| auth_code | 邮箱授权码（非密码） |

**QQ邮箱授权码获取**：QQ邮箱设置 → 账户 → POP3/SMTP服务 → 生成授权码

### 知识库配置

知识库已内置充电桩相关知识，包括：
- 扫码充电指引
- 故障处理方法
- 计费问题解答

## 测试场景

```json
// 1. 使用指导
{"user_message": "充电桩怎么使用"}

// 2. 故障处理
{"user_message": "充电停不下来了，点了停止按钮还在继续充电"}

// 3. 投诉兜底
{"user_message": "我要投诉，充电扣了50块但只充了20块的电，我的手机号是13800138000"}

// 4. 评价反馈
{"user_message": "1"}  // 或 "2"

// 5. 多轮对话
{"user_message": "充电桩怎么使用", "user_id": "user_001"}
```

## 技术栈

- Python 3.9
- LangGraph 1.0
- LangChain 1.0
- Supabase（数据库）
- Coze 平台

## 文件结构

```
src/
├── graphs/
│   ├── state.py          # 状态定义
│   ├── graph.py          # 主图编排
│   └── nodes/            # 节点实现
│       ├── load_history_node.py
│       ├── save_history_node.py
│       ├── save_record_node.py
│       ├── intent_recognition_node.py
│       ├── knowledge_qa_node.py
│       ├── feedback_node.py
│       ├── info_collection_node.py
│       └── email_sending_node.py
├── storage/
│   └── database/
│       └── supabase_client.py
└── main.py               # 入口文件

config/
├── intent_recognition_llm_cfg.json
├── knowledge_qa_llm_cfg.json
└── info_collection_llm_cfg.json
```

## 对接企业微信

工作流支持通过腾讯云函数对接企业微信，详见 [GitHub 文档](https://github.com/franksong2702/wechat-ai-scf/blob/main/docs/coze-multi-turn-design.md)。

关键参数：
- `user_id`：企业微信的 `external_userid`，用于多轮对话

## 更新日志

### v1.1.0 (2026-03-28)
- 新增多轮对话支持（user_id）
- 新增对话记录保存（Supabase）
- 新增评价记录保存
- 修复文件写入权限问题

### v1.0.0
- 初始版本
- 支持意图识别、知识库问答、投诉处理、评价反馈
