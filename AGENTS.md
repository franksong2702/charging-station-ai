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
        ├─ 使用指导/故障处理 → knowledge_qa (知识库问答)
        ├─ 兜底流程 → fallback (兜底处理)
        ├─ 轻度不满 → dissatisfied (轻度不满处理)
        ├─ 满意 → satisfied (满意处理)
        ├─ 评价反馈 → feedback (评价处理)
        └─ 退出兜底 → clear_fallback_state (清除状态) → knowledge_qa
```

### 节点清单
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
| info_collection | `nodes/info_collection_node.py` | agent | 投诉信息收集（旧流程兼容） | `config/info_collection_llm_cfg.json` |

**类型说明**: task(普通节点) / agent(大模型节点) / condition(条件分支)

### 条件节点
| 节点名 | 文件位置 | 输入类型 | 功能描述 | 分支逻辑 |
|-------|---------|---------|---------|---------|
| cond_intent_recognition | `graph.py` | IntentRouteCheck | 意图路由 | "使用指导"/"故障处理"→knowledge_qa, "兜底流程"→fallback, "不满意"→dissatisfied, "满意"→satisfied, "评价反馈"→feedback, "退出兜底"→clear_fallback_state |
| cond_fallback | `graph.py` | CaseConfirmedCheck | 工单确认判断 | "创建工单"→create_case, "继续兜底"→save_history |

## 意图类型

| 意图 | 触发条件 | 处理节点 |
|-----|---------|---------|
| usage_guidance | 使用指导类问题 | knowledge_qa |
| fault_handling | 故障处理类问题 | knowledge_qa |
| fallback | 强烈不满/转人工 | fallback |
| dissatisfied | 轻度不满 | dissatisfied |
| satisfied | 用户表达感谢 | satisfied |
| feedback_good | 评价"1"或"很好" | feedback |
| feedback_bad | 评价"2"或"没有帮助" | feedback |
| exit_fallback | 退出兜底流程 | clear_fallback_state |
| cancel_fallback | 取消兜底流程 | clear_fallback_state |

## 兜底流程设计

### 流程阶段
```
collect_info (收集信息) → confirm (用户确认) → done (完成)
```

### 触发条件
- 强烈不满关键词：太差了、垃圾、投诉你、转人工等
- 转人工关键词：转人工、人工客服、接人工等

### 信息收集
- 手机号：LLM 智能提取，支持各种格式
- 车牌号：LLM 智能提取，支持新能源车牌等

### 取消机制
用户可在任何阶段取消，关键词：取消、不用了、算了等

## 数据库设计
- `conversation_history`：对话历史和兜底流程状态
- `case_records`：工单记录

## 技能使用
- 大语言模型：`LLMClient` (coze-coding-dev-sdk)
- 知识库：`KnowledgeClient` (coze-coding-dev-sdk)
- 邮件发送：`EmailClient` (coze-coding-dev-sdk)
- 数据库：Supabase

## 邮件配置
收件邮箱：xuefu.song@qq.com
