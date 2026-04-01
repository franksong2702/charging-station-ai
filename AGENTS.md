# 充电桩智能客服工作流

## 项目概述
- **名称**: 充电桩智能客服
- **功能**: 基于LangGraph的智能客服工作流，支持使用指导、故障处理、兜底流程、工单系统、评价反馈和多轮对话

## 工作流结构

```
load_history (加载对话历史)
        │
        ▼
intent_recognition (意图识别)
        │
        ├─ 使用指导/故障处理 → knowledge_qa → save_history → save_record → END
        ├─ 兜底流程 → fallback → [创建工单/继续兜底]
        ├─ 轻度不满 → dissatisfied → save_record → END
        ├─ 满意 → satisfied → save_record → END
        ├─ 评价反馈 → feedback → save_record → END
        └─ 退出兜底 → clear_fallback_state → knowledge_qa
```

## 节点清单

| 节点名 | 文件位置 | 类型 | 功能描述 | 配置文件 |
|-------|---------|------|---------|---------|
| load_history | `nodes/load_history_node.py` | task | 加载对话历史和兜底状态 | - |
| intent_recognition | `nodes/intent_recognition_node.py` | agent | 意图识别 | `config/intent_recognition_llm_cfg.json` |
| knowledge_qa | `nodes/knowledge_qa_node.py` | agent | 知识库问答 | `config/knowledge_qa_llm_cfg.json` |
| dissatisfied | `nodes/dissatisfied_node.py` | task | 轻度不满处理 | - |
| satisfied | `nodes/satisfied_node.py` | task | 满意处理 | - |
| feedback | `nodes/feedback_node.py` | task | 评价反馈处理 | - |
| fallback | `nodes/fallback_node.py` | task | 兜底流程处理 | - |
| create_case | `nodes/create_case_node.py` | task | 创建工单 | - |
| email_sending | `nodes/email_sending_node.py` | task | 发送邮件 | - |
| clear_fallback_state | `nodes/clear_fallback_state_node.py` | task | 清除兜底状态 | - |
| save_history | `nodes/save_history_node.py` | task | 保存对话历史 | - |
| save_record | `nodes/save_record_node.py` | task | 保存对话记录 | - |

**类型说明**: task(普通节点) / agent(大模型节点)

## 条件节点

| 节点名 | 文件位置 | 输入类型 | 功能描述 | 分支逻辑 |
|-------|---------|---------|---------|---------|
| cond_intent_recognition | `graph.py` | IntentRouteCheck | 意图路由 | 见下表 |
| cond_fallback | `graph.py` | CaseConfirmedCheck | 工单确认判断 | "创建工单"→create_case, "继续兜底"→save_history |

### cond_intent_recognition 分支逻辑

| 返回值 | 目标节点 | 触发条件 |
|-------|---------|---------|
| 使用指导 | knowledge_qa | intent = "usage_guidance" |
| 故障处理 | knowledge_qa | intent = "fault_handling" |
| 兜底流程 | fallback | intent = "fallback" / "complaint" |
| 不满意 | dissatisfied | intent = "dissatisfied" |
| 满意 | satisfied | intent = "satisfied" |
| 评价反馈 | feedback | intent = "feedback_good" / "feedback_bad" |
| 退出兜底 | clear_fallback_state | intent = "exit_fallback" / "cancel_fallback" |

## 意图识别规则

| 意图类型 | 触发关键词/条件 |
|---------|----------------|
| usage_guidance | 使用指导类问题（默认） |
| fault_handling | 充不进去、充不上、充电失败、坏了、故障等 |
| fallback | 垃圾、投诉、转人工、强烈不满 |
| dissatisfied | 没用、不行、没帮助、轻度不满 |
| satisfied | 谢谢、感谢、满意 |
| feedback_good | "1"、"很好"、"有帮助" |
| feedback_bad | "2"、"没有帮助"、"没用" |

## 兜底流程状态

| 状态值 | 含义 | 行为 |
|-------|------|------|
| `""` (空) | 不在兜底流程中 | 正常对话 |
| `"collect_info"` | 收集信息中 | 继续收集手机号/车牌号 |
| `"confirm"` | 等待用户确认 | 用户确认后 → done |
| `"done"` | 已完成 | 不保存状态，下次是新会话 |

## 数据库设计

- `conversation_history`: 对话历史和兜底流程状态
- `dialog_records`: 有价值的对话记录（评价/不满意）
- `case_records`: 工单记录

## 技能使用

- 大语言模型：`LLMClient` (coze-coding-dev-sdk)
- 知识库：`KnowledgeClient` (coze-coding-dev-sdk)
- 邮件发送：`EmailClient` (coze-coding-dev-sdk)
- 数据库：Supabase

## 邮件配置

收件邮箱：xuefu.song@qq.com
