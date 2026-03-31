# 充电桩智能客服工作流

## 项目概述
- **名称**: 充电桩智能客服
- **功能**: 基于LangGraph的智能客服工作流，支持使用指导、故障处理、兜底流程、工单系统、评价反馈和多轮对话

### 节点清单
| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 | 配置文件 |
|-------|---------|------|---------|---------|---------|
| input_process | `nodes/input_process_node.py` | task | 输入预处理 | - | - |
| load_history | `nodes/load_history_node.py` | task | 加载对话历史和兜底状态 | - | - |
| asr_node | `nodes/asr_node.py` | task | 语音转文字 | - | - |
| intent_recognition | `nodes/intent_recognition_node.py` | agent | 意图识别（区分强烈不满/轻度不满/退出兜底） | - | `config/intent_recognition_llm_cfg.json` |
| knowledge_qa | `nodes/knowledge_qa_node.py` | agent | 知识库问答 | - | `config/knowledge_qa_llm_cfg.json` |
| dissatisfied | `nodes/dissatisfied_node.py` | agent | 轻度不满处理（道歉+询问详情） | - | `config/dissatisfied_llm_cfg.json` |
| satisfied | `nodes/satisfied_node.py` | agent | 满意处理（感谢+请求评价） | - | `config/satisfied_llm_cfg.json` |
| feedback | `nodes/feedback_node.py` | agent | 评价反馈处理 | - | `config/feedback_llm_cfg.json` |
| fallback | `nodes/fallback_node.py` | agent | 兜底流程（收集信息→生成总结→确认，支持取消） | - | `config/fallback_llm_cfg.json` |
| create_case | `nodes/create_case_node.py` | task | 创建工单（内部流转） | - | - |
| email_sending | `nodes/email_sending_node.py` | task | 发送邮件（支持重试3次） | - | - |
| clear_fallback_state | `nodes/clear_fallback_state_node.py` | task | 清除兜底状态（退出兜底时识别新意图） | - | - |
| save_record | `nodes/save_record_node.py` | task | 保存对话记录（仅有价值记录） | - | - |
| save_history | `nodes/save_history_node.py` | task | 保存对话历史和兜底状态 | - | - |

**类型说明**: task(task节点) / agent(大模型) / condition(条件分支)

### 条件节点
| 节点名 | 文件位置 | 功能描述 | 分支逻辑 |
|-------|---------|---------|---------|
| route_by_voice_input | `graph.py` | 判断是否有语音输入 | "语音处理"→asr, "直接处理文字"→intent_recognition |
| route_by_intent | `graph.py` | 意图路由 | "使用指导"/"故障处理"→knowledge_qa, "兜底流程"→fallback, "不满意"→dissatisfied, "满意"→satisfied, "评价反馈"→feedback, "退出兜底"→clear_fallback_state→knowledge_qa |
| route_by_case_confirmed | `graph.py` | 工单确认判断 | "创建工单"→create_case, "继续兜底"→save_history |

## 子图清单
无

## 技能使用
- 大语言模型：`LLMClient` (coze-coding-dev-sdk)
- 知识库：`KnowledgeBaseClient` (coze-coding-dev-sdk)
- 语音识别：`ASRClient` (coze-coding-dev-sdk)
- 邮件发送：`EmailClient` (coze-coding-dev-sdk)
- 数据库：Supabase

## 意图识别规则

### 强烈不满/转人工 → 兜底流程
关键词：太差了、垃圾、投诉你、什么破、转人工、人工客服

### 轻度不满 → AI 继续尝试帮助
关键词：没用、不行、还是不行、没帮助、**为什么没有**、**什么时候**、**怎么没有**

### 使用指导
关于如何扫码、如何使用充电桩、找不到二维码等首次使用问题

### 故障处理
充电停不下来、枪拔不出来、充电失败、充电速度慢等设备或操作故障

### 退出兜底（重要）
**当用户在兜底流程中问新问题时，自动退出兜底流程：**
- 用户发送明显的新问题（包含"怎么"、"如何"、"为什么"等）
- 用户发送取消关键词（"取消"、"不用了"、"算了"等）

**智能判断逻辑**：
1. 如果用户输入的是手机号/车牌号/确认等兜底相关信息 → 继续兜底
2. 如果用户输入的是新问题 → 退出兜底，正常处理问题
3. 如果用户取消 → 退出兜底，提示用户

## 兜底流程设计

### 触发条件
- **强烈不满关键词**: "太差了"、"垃圾"、"什么破系统"、"投诉你"等
- **转人工关键词**: "转人工"、"人工客服"、"接人工"等

### 流程阶段
```
用户触发兜底 → collect_info（收集信息）→ confirm（用户确认）→ 创建工单 → 发送邮件 → 结束
```

### 信息提取（LLM 智能提取）
- **手机号**：LLM 智能识别，支持各种格式（带横线、括号、空格、中文数字等）
- **车牌号**：LLM 智能识别，支持新能源车牌、带空格格式等

### 取消机制
用户可以在任何阶段取消，回复关键词："取消"、"不用了"、"算了"、"不需要了"等

### 工单处理
- 工单信息仅用于内部流转，不向用户展示工单号
- 用户无需通过工单号查询，工作人员会主动联系

## 数据库设计
### conversation_history 表
用于多轮对话历史和兜底流程状态管理
- user_id: 用户标识
- user_message: 用户消息
- reply_content: AI回复
- intent: 意图类型
- fallback_phase: 兜底流程阶段（collect_info/confirm/done）
- phone: 手机号
- license_plate: 车牌号
- problem_summary: 问题总结

### case_records 表
用于工单管理（内部流转）
- id: 工单ID
- user_id: 用户标识
- phone: 手机号
- license_plate: 车牌号
- problem_summary: 问题总结
- status: 工单状态（pending/processing/resolved/closed）

## 邮件配置
需要通过 Coze 平台配置邮箱集成凭证 `integration-email-imap-smtp`：
- account: 发件邮箱地址
- auth_code: 邮箱授权码
- smtp_server: SMTP服务器地址
- smtp_port: SMTP端口（SSL加密通常为465）

收件邮箱：xuefu.song@qq.com
