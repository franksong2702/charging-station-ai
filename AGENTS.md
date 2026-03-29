## 项目概述
- **名称**: 充电桩智能客服工作流
- **功能**: 为充电桩小程序提供智能客服服务，支持文字和语音输入，支持智能评价触发、多轮对话、转人工和对话记录保存

### 节点清单
| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 | 配置文件 |
|-------|---------|------|---------|---------|---------|
| load_history | `nodes/load_history_node.py` | task | 根据用户ID加载对话历史 | - | - |
| input_process | `nodes/input_process_node.py` | task | 判断输入类型（文字/语音） | - | - |
| route_by_voice_input | `graph.py` | condition | 根据是否有语音URL决定分支 | "语音处理"→asr, "直接处理文字"→intent_recognition | - |
| asr | `nodes/asr_node.py` | task | 语音转文字（ASR） | - | - |
| intent_recognition | `nodes/intent_recognition_node.py` | agent | 识别用户问题类型（6种意图） | - | `config/intent_recognition_llm_cfg.json` |
| route_by_intent | `graph.py` | condition | 根据意图路由到不同处理流程 | 见下方路由表 | - |
| knowledge_qa | `nodes/knowledge_qa_node.py` | agent | 搜索知识库并生成回复（智能评价触发） | - | `config/knowledge_qa_llm_cfg.json` |
| save_history | `nodes/save_history_node.py` | task | 保存对话历史到数据库（用于多轮对话） | - | - |
| save_record | `nodes/save_record_node.py` | task | 保存对话记录到数据库（用于分析） | - | - |
| feedback | `nodes/feedback_node.py` | task | 处理用户评价反馈（很好/没有帮助） | - | - |
| dissatisfied | `nodes/dissatisfied_node.py` | task | 处理用户不满，提供选择（重新描述/转人工） | - | - |
| info_collection | `nodes/info_collection_node.py` | agent | 提取用户信息（手机号、订单号、问题描述） | - | `config/info_collection_llm_cfg.json` |
| email_sending | `nodes/email_sending_node.py` | task | 发送信息到客服邮箱 | - | - |

**类型说明**: task(task节点) / agent(大模型) / condition(条件分支) / looparray(列表循环) / loopcond(条件循环)

### 意图路由表
| 意图 | 路由目标 | 说明 |
|-----|---------|------|
| usage_guidance | knowledge_qa | 使用指导 → 知识库问答 |
| fault_handling | knowledge_qa | 故障处理 → 知识库问答 |
| complaint | info_collection | 投诉兜底 → 信息收集 → 邮件发送 |
| transfer_human | info_collection | 转人工 → 信息收集 → 邮件发送 |
| dissatisfied | dissatisfied | 不满意 → 友好询问 |
| feedback_good | feedback | 评价好 → 记录感谢 |
| feedback_bad | feedback | 评价差 → 记录引导 |

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
                            ├── 使用指导/故障处理 → 【知识库问答】→ 智能判断是否触发评价 → 【保存历史】→ 【保存记录】
                            │
                            ├── 投诉兜底/转人工 → 【信息收集】→ 【邮件发送】→ 【保存记录】→ 告知用户已收到
                            │
                            ├── 不满意 → 【友好询问】→ 提供选择（重新描述/转人工）
                            │
                            └── 评价反馈（1/2）→ 【评价处理】→ 【保存记录】→ 回复用户
```

## 智能评价触发
评价触发由 LLM 智能判断，规则如下：

### 触发评价
- 提供了完整的解决方案或操作指导
- 用户表示感谢（"谢谢"、"好的"、"明白了"等）
- 问题已经得到解答

### 不触发评价
- 用户明确表示不满（"没用"、"不行"、"太差了"等）
- 用户要求转人工客服
- 用户在投诉或抱怨

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

## 多轮对话
- **存储方式**: Supabase 数据库
- **表名**: conversation_history
- **最大历史轮数**: 10 轮
- **兼容性**: 无 user_id 时正常工作（单轮对话）

## 评价机制
- 触发方式：LLM 智能判断
- 评价选项：回复【1】很好 / 回复【2】没有帮助
- 支持格式：半角数字(1/2)、全角数字(１/２)、带括号格式(【1】/【２】)
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
1. **文字输入 - 使用指导场景**: "充电桩怎么用？"
2. **文字输入 - 故障处理场景**: "充电枪拔不出来怎么办？"
3. **文字输入 - 投诉场景**: "我刚才充电扣了50块钱，但是实际只充了20块钱，要求退款！"
4. **文字输入 - 转人工场景**: "我要转人工客服"
5. **文字输入 - 不满意场景**: "这回答没用，太差了"
6. **评价反馈场景**: 用户回复 "1" 或 "2" 进行评价
7. **多轮对话场景**: 传入 user_id 参数，AI会记住之前的对话上下文

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
- ✅ 智能评价：LLM 判断是否触发评价
- ❌ 图片输入：暂不支持
- ❌ 图片输出：暂不支持
