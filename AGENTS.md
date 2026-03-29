## 项目概述
- **名称**: 充电桩智能客服工作流
- **功能**: 为充电桩小程序提供智能客服服务，支持文字和语音输入，支持兜底流程、工单系统、多轮对话和对话记录保存

### 节点清单
| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 | 配置文件 |
|-------|---------|------|---------|---------|---------|
| load_history | `nodes/load_history_node.py` | task | 根据用户ID加载对话历史 | - | - |
| input_process | `nodes/input_process_node.py` | task | 判断输入类型（文字/语音） | - | - |
| route_by_voice_input | `graph.py` | condition | 根据是否有语音URL决定分支 | "语音处理"→asr, "直接处理文字"→intent_recognition | - |
| asr | `nodes/asr_node.py` | task | 语音转文字（ASR） | - | - |
| intent_recognition | `nodes/intent_recognition_node.py` | agent | 识别用户问题类型（6种意图） | - | `config/intent_recognition_llm_cfg.json` |
| route_by_intent | `graph.py` | condition | 根据意图路由到不同处理流程 | 见下方路由表 | - |
| knowledge_qa | `nodes/knowledge_qa_node.py` | agent | 搜索知识库并生成回复 | - | `config/knowledge_qa_llm_cfg.json` |
| save_history | `nodes/save_history_node.py` | task | 保存对话历史到数据库（用于多轮对话） | - | - |
| save_record | `nodes/save_record_node.py` | task | 保存有价值的对话记录（评价/不满意） | - | - |
| feedback | `nodes/feedback_node.py` | task | 处理用户评价反馈（很好/没有帮助） | - | - |
| dissatisfied | `nodes/dissatisfied_node.py` | task | 处理轻度不满，请求详细描述问题 | - | - |
| satisfied | `nodes/satisfied_node.py` | task | 用户满意时，感谢用户并请求评价 | - | - |
| fallback | `nodes/fallback_node.py` | task | 兜底流程，收集信息并确认问题总结 | - | - |
| create_case | `nodes/create_case_node.py` | task | 创建工单记录 | - | - |
| info_collection | `nodes/info_collection_node.py` | agent | 提取用户信息（投诉场景） | - | `config/info_collection_llm_cfg.json` |
| email_sending | `nodes/email_sending_node.py` | task | 发送工单信息到客服邮箱 | - | - |

**类型说明**: task(task节点) / agent(大模型) / condition(条件分支) / looparray(列表循环) / loopcond(条件循环)

### 意图路由表
| 意图 | 路由目标 | 说明 |
|-----|---------|------|
| usage_guidance | knowledge_qa | 使用指导 → 知识库问答 |
| fault_handling | knowledge_qa | 故障处理 → 知识库问答 |
| complaint | fallback | 投诉兜底 → 兜底流程 |
| fallback | fallback | 强烈不满/转人工 → 兜底流程 |
| dissatisfied | dissatisfied | 轻度不满 → AI继续尝试帮助 |
| satisfied | satisfied | 满意 → 感谢并请求评价 |
| feedback_good | feedback | 评价好 → 记录感谢 |
| feedback_bad | feedback | 评价差 → 记录引导 |

## 子图清单
无子图

## 技能使用
- 节点 `asr` 使用技能：ASR 语音识别
- 节点 `intent_recognition` 使用技能：大语言模型
- 节点 `knowledge_qa` 使用技能：大语言模型, 知识库
- 节点 `fallback` 使用技能：大语言模型
- 节点 `info_collection` 使用技能：大语言模型
- 节点 `email_sending` 使用技能：邮件
- 节点 `load_history` 使用技能：Supabase
- 节点 `save_history` 使用技能：Supabase
- 节点 `save_record` 使用技能：Supabase
- 节点 `create_case` 使用技能：Supabase

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
                            ├── 使用指导/故障处理 → 【知识库问答】→ 【保存历史】→ 【保存记录】
                            │
                            ├── 轻度不满 → 【道歉并请求描述】→ 【保存记录】
                            │
                            ├── 满意 → 【感谢并请求评价】→ 【保存记录】
                            │
                            ├── 强烈不满/转人工/投诉 → 【兜底流程】
                            │                               ↓
                            │                        收集手机号、车牌号
                            │                               ↓
                            │                        生成问题总结
                            │                               ↓
                            │                        用户确认/补充（循环）
                            │                               ↓
                            │                        【创建工单】→ 【发送邮件】
                            │
                            └── 评价反馈（1/2）→ 【评价处理】→ 【保存记录】
```

## 智能评价触发
评价触发由意图识别节点判断，规则如下：

### 触发评价
- **用户表达满意**：说"谢谢"、"感谢"、"好的好的"等感谢词

### 不触发评价
- 用户表达不满
- 用户要求转人工客服
- 第一次回答（避免过于频繁请求评价）

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
用于保存有价值的对话记录，用于知识库优化。

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

**只保存以下场景**：
- 评价反馈（满意/不满意）
- 不满意反馈

### case_records（工单表）
用于保存需要人工处理的工单记录。

```sql
CREATE TABLE case_records (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(128),
    phone VARCHAR(20),
    license_plate VARCHAR(20),
    problem_summary TEXT,
    conversation_context JSONB,
    case_type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolution_note TEXT
);
```

**创建时机**：
- 兜底流程用户确认后

## 多轮对话
- **存储方式**: Supabase 数据库
- **表名**: conversation_history
- **最大历史轮数**: 10 轮
- **兼容性**: 无 user_id 时正常工作（单轮对话）

## 兜底流程
当用户强烈不满或要求转人工时，触发兜底流程：

1. **收集信息**：请求用户提供手机号、车牌号
2. **生成总结**：AI 从对话历史生成问题总结
3. **用户确认**：展示总结，用户可补充或确认
4. **创建工单**：保存到 case_records 表
5. **发送邮件**：通知客服团队

## 输入输出格式

### 输入参数
```json
{
  "user_message": "用户发送的文字消息",
  "voice_url": "用户发送的语音URL（可选）",
  "user_id": "用户身份标识（可选，用于多轮对话）",
  "fallback_phase": "兜底流程阶段（可选）",
  "phone": "已收集的手机号（可选）",
  "license_plate": "已收集的车牌号（可选）",
  "problem_summary": "已生成的问题总结（可选）"
}
```

### 输出参数
```json
{
  "reply_content": "AI客服的回复内容"
}
```

## 测试用例
详见 `docs/测试用例.md`
