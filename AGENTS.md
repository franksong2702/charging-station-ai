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
| intent_recognition | `nodes/intent_recognition_node.py` | agent | 意图识别（区分强烈不满/轻度不满） | - | `config/intent_recognition_llm_cfg.json` |
| knowledge_qa | `nodes/knowledge_qa_node.py` | agent | 知识库问答 | - | `config/knowledge_qa_llm_cfg.json` |
| dissatisfied | `nodes/dissatisfied_node.py` | agent | 轻度不满处理（道歉+询问详情） | - | `config/dissatisfied_llm_cfg.json` |
| satisfied | `nodes/satisfied_node.py` | agent | 满意处理（感谢+请求评价） | - | `config/satisfied_llm_cfg.json` |
| feedback | `nodes/feedback_node.py` | agent | 评价反馈处理 | - | `config/feedback_llm_cfg.json` |
| fallback | `nodes/fallback_node.py` | agent | 兜底流程（收集信息→生成总结→确认） | - | `config/fallback_llm_cfg.json` |
| create_case | `nodes/create_case_node.py` | task | 创建工单 | - | - |
| email_sending | `nodes/email_sending_node.py` | task | 发送邮件 | - | - |
| clear_fallback_state | `nodes/clear_fallback_state_node.py` | task | 清除兜底状态 | - | - |
| save_record | `nodes/save_record_node.py` | task | 保存对话记录（仅有价值记录） | - | - |
| save_history | `nodes/save_history_node.py` | task | 保存对话历史和兜底状态 | - | - |

**类型说明**: task(task节点) / agent(大模型) / condition(条件分支)

### 条件节点
| 节点名 | 文件位置 | 功能描述 | 分支逻辑 |
|-------|---------|---------|---------|
| route_by_voice | `graph.py` | 判断是否有语音输入 | "语音处理"→asr_node, "直接处理文字"→load_history |
| route_by_intent | `graph.py` | 意图路由 | "使用指导"/"故障处理"→knowledge_qa, "兜底流程"→fallback, "不满意"→dissatisfied, "满意"→satisfied, "评价反馈"→feedback |
| route_by_case_confirmed | `graph.py` | 工单确认判断 | "创建工单"→create_case, "继续兜底"→fallback |

## 子图清单
无

## 技能使用
- 大语言模型：`LLMClient` (coze-coding-dev-sdk)
- 知识库：`KnowledgeBaseClient` (coze-coding-dev-sdk)
- 语音识别：`ASRClient` (coze-coding-dev-sdk)
- 邮件发送：`EmailClient` (coze-coding-dev-sdk)
- 数据库：Supabase

## 数据库设计
### conversation_history 表
用于多轮对话历史和兜底流程状态管理
- user_id: 用户标识
- user_message: 用户消息
- reply_content: AI回复
- intent: 意图类型
- fallback_phase: 兜底流程阶段（collect_info/summarize/confirm/send）
- phone: 手机号
- license_plate: 车牌号
- problem_summary: 问题总结

### case_records 表
用于工单管理
- case_id: 工单ID
- user_id: 用户标识
- phone: 手机号
- license_plate: 车牌号
- problem_summary: 问题总结
- status: 工单状态（pending/processing/resolved/closed）
