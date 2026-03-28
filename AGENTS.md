## 项目概述
- **名称**: 充电桩智能客服工作流
- **功能**: 为充电桩小程序提供智能客服服务，支持文字和语音输入，支持评价机制、多轮对话和对话记录保存

### 节点清单
| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 | 配置文件 |
|-------|---------|------|---------|---------|---------|
| load_history | `nodes/load_history_node.py` | task | 根据用户ID加载对话历史 | - | - |
| input_process | `nodes/input_process_node.py` | task | 判断输入类型（文字/语音） | - | - |
| route_by_voice_input | `graph.py` | condition | 根据是否有语音URL决定分支 | "语音处理"→asr, "直接处理文字"→intent_recognition | - |
| asr | `nodes/asr_node.py` | task | 语音转文字（ASR） | - | - |
| intent_recognition | `nodes/intent_recognition_node.py` | agent | 识别用户问题类型（使用指导/故障处理/投诉兜底/评价反馈） | - | `config/intent_recognition_llm_cfg.json` |
| route_by_intent | `graph.py` | condition | 根据意图路由到不同处理流程 | "使用指导"→knowledge_qa, "故障处理"→knowledge_qa, "投诉兜底"→info_collection, "评价反馈"→feedback | - |
| knowledge_qa | `nodes/knowledge_qa_node.py` | agent | 搜索知识库并生成回复（含评价提示） | - | `config/knowledge_qa_llm_cfg.json` |
| save_history | `nodes/save_history_node.py` | task | 保存对话历史到数据库（用于多轮对话） | - | - |
| save_record | `nodes/save_record_node.py` | task | 保存对话记录到数据库（用于分析） | - | - |
| feedback | `nodes/feedback_node.py` | task | 处理用户评价反馈（很好/没有帮助） | - | - |
| info_collection | `nodes/info_collection_node.py` | agent | 提取用户投诉信息（手机号、订单号、问题描述） | - | `config/info_collection_llm_cfg.json` |
| email_sending | `nodes/email_sending_node.py` | task | 发送投诉信息到客服邮箱 | - | - |

**类型说明**: task(task节点) / agent(大模型) / condition(条件分支) / looparray(列表循环) / loopcond(条件循环)

## 子图清单
无子图

## 技能使用
- 节点 `asr` 使用技能：ASR 语音识别
- 节点 `intent_recognition` 使用技能：大语言模型
- 节点 `knowledge_qa` 使用技能：大语言模型, 知识库
- 节点 `info_collection` 使用技能：大语言模型
- 节点 `email_sending` 使用技能：邮件
- 节点 `load_history` 使用技能：Supabase
- 节点 `save_history` 使用技能：Supabase
- 节点 `save_record` 使用技能：Supabase

## 知识库
- 数据集名称: `charging_station_kb`
- 文档ID: `7619187998604853258`
- 内容: 充电桩知识库.md（包含扫码指引、故障处理、计费问题等）

## 工作流逻辑
```
用户输入（文字或语音）+ user_id（可选）
    ↓
【加载对话历史】→ 根据user_id加载历史（支持多轮对话）
    ↓
【输入预处理】→ 判断输入类型
    ↓
    ├── 有语音URL → 【ASR语音转文字】→ 【意图识别】
    │                                    ↓
    └── 无语音（纯文字）→ 【意图识别】→ 判断问题类型
                            ↓
                            ├── 使用指导/故障处理 → 【知识库问答】→ 【保存历史】→ 【保存记录】→ 回复用户（含评价提示）
                            │
                            ├── 投诉兜底 → 【信息收集】→ 【邮件发送】→ 【保存记录】→ 告知用户已收到
                            │
                            └── 评价反馈（1/2）→ 【评价处理】→ 【保存记录】→ 回复用户
```

## 数据库表

### conversation_history（对话历史表）
用于多轮对话上下文，存储最近的对话记录。

```sql
CREATE TABLE conversation_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,
    user_message TEXT NOT NULL,
    reply_content TEXT NOT NULL,
    intent VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### dialog_records（对话记录表）
用于保存所有对话和评价记录，用于后续分析。

```sql
CREATE TABLE dialog_records (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(128),
    user_message TEXT NOT NULL,
    reply_content TEXT NOT NULL,
    intent VARCHAR(50),
    feedback_type VARCHAR(20),
    knowledge_matched BOOLEAN DEFAULT FALSE,
    knowledge_chunks JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```
                            ├── 使用指导/故障处理 → 【知识库问答】→ 【保存历史】→ 回复用户（含评价提示）
                            │
                            ├── 投诉兜底 → 【信息收集】→ 【邮件发送】→ 告知用户已收到
                            │
                            └── 评价反馈（1/2）→ 【评价处理】→ 回复用户
```

## 多轮对话
- **存储方式**: Supabase 数据库
- **表名**: conversation_history
- **最大历史轮数**: 10 轮
- **兼容性**: 无 user_id 时正常工作（单轮对话）

### 对话历史表结构
```sql
CREATE TABLE conversation_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,
    user_message TEXT NOT NULL,
    reply_content TEXT NOT NULL,
    intent VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 评价机制
- 触发场景：知识库问答后
- 评价选项：回复【1】很好 / 回复【2】没有帮助
- 记录保存：对话记录保存到 Supabase 数据库

## 输入输出格式

### 输入参数
```json
{
  "user_message": "用户发送的文字消息",
  "voice_url": "用户发送的语音URL（可选）",
  "user_id": "用户身份标识（可选，用于多轮对话）"
}
```

### 输出参数
```json
{
  "reply_content": "AI客服的回复内容"
}
```

## 测试场景
1. **文字输入 - 使用指导场景**: "我看到充电桩上有很多二维码，不知道应该扫哪一个？我是特斯拉的车。"
2. **文字输入 - 故障处理场景**: "充电停不下来了，我点了停止按钮但是还在继续充电，怎么办？"
3. **文字输入 - 投诉兜底场景**: "我刚才充电扣了50块钱，但是实际只充了20块钱的电，要求退款！我的手机号是13800138000，订单号是12345678"
4. **语音输入场景**: 传入 voice_url 参数，ASR自动转文字后处理
5. **评价反馈场景**: 用户回复 "1" 或 "2" 进行评价
6. **多轮对话场景**: 传入 user_id 参数，AI会记住之前的对话上下文

## 邮件配置说明
邮件发送功能需要配置SMTP服务器信息。当前配置的收件邮箱为：`xuefu.song@qq.com`

配置步骤：
1. 在平台集成配置中添加邮件集成（integration-email-imap-smtp）
2. 配置SMTP服务器地址、端口、账号和授权码
3. 工作流会自动从集成配置中读取邮件发送信息

## 多模态支持
- ✅ 文字输入：直接处理
- ✅ 语音输入：ASR 转文字后处理
- ✅ 多轮对话：通过 user_id 支持上下文
- ❌ 图片输入：暂不支持
- ❌ 图片输出：暂不支持
