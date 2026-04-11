# 充电桩智能客服工作流

## 项目概述
- **名称**: 充电桩智能客服
- **功能**: 基于LangGraph的智能客服工作流，支持使用指导、故障处理、兜底流程、工单系统、评价反馈和多轮对话

---

## 🎯 核心设计理念

### 1. LLM 优先，关键词兜底
- **原则**: 能用 LLM 解决的问题，就不要用正则表达式和关键词匹配
- **实践**: 意图识别、查询改写、退出判断都优先使用 LLM，关键词仅作为兜底机制
- **效果**: 语义理解更准确，覆盖更多 corner case

### 2. 简单直接，用户体验第一
- **兜底流程**: 放弃死板的顺序收集（先手机号、后车牌号、最后问题），改为用户随意提供信息，系统随时记录和更新
- **话术优化**: 避免车轱辘话，保持自然简洁，用户要改什么就直接改，不用从头开始
- **评价时机**: 不"贴脸"问评价，改为用户表示满意/感谢时自然触发

### 3. 全量对话保存，上下文利用
- **图结构优化**: 确保所有分支（评价反馈、轻度不满、满意、兜底流程）都先经过 `save_history` 节点
- **上下文传递**: 在 `knowledge_qa_node` 中将最近 10 轮对话作为上下文传给 LLM，提升回复连贯性和人情味
- **兜底状态过期**: 兜底流程状态 30 分钟自动过期，避免用户永久卡在兜底流程

### 4. 知识库质量优先，搜索策略多样
- **数据清洗**: 过滤无效内容（空片段、"nan"值、填写说明行）
- **查询改写**: 使用 LLM 将口语化问题改写为精准搜索词，根据意图类型添加相关关键词
- **搜索参数**: 降低 `min_score`（0.4），增加 `top_k`（10），确保返回更多相关内容
- **内容识别**: 扩展有效内容格式支持（编号列表、列表项、时间范围、费用信息等）

---

## 💡 经验与教训

### 经验总结

#### 1. 关于 LLM 使用
- **提示词工程很重要**: 清晰的角色定义、任务边界、输出格式要求，可以显著提升 LLM 表现
- **上下文信息要充分**: 在兜底流程中，把当前阶段、问题总结、用户问题描述都传给 LLM，帮助模型理解场景
- **输出解析要容错**: LLM 可能返回格式不完美的结果，解析时要有容错机制

#### 2. 关于状态管理
- **状态要有过期机制**: 任何流程状态都不应该永久保存，必须有过期或重置机制
- **时区问题要注意**: 数据库时间带时区，代码时间不带时区，计算时间差时要统一处理
- **状态保存要及时**: 所有对话都应该先保存到数据库，再进行后续处理

#### 3. 关于用户体验
- **不要过度设计**: 简单直接的流程往往比复杂的流程更好用
- **不要"聪明"过度**: 不要试图猜测用户意图，给用户明确的选项和操作指引
- **不要死记硬背**: 用户要改什么就直接改，不要强制用户按固定顺序操作

#### 4. 关于知识库
- **数据质量是基础**: 垃圾进，垃圾出。必须先清洗知识库数据
- **搜索参数要调优**: `min_score` 和 `top_k` 需要根据实际数据调整
- **结果过滤要谨慎**: 不要过滤掉可能有用的内容，宁可多返回一些让 LLM 判断

### 踩过的坑

#### 1. 兜底流程永久卡住
- **问题**: 兜底流程状态没有过期机制，用户永久卡在兜底流程
- **解决**: 添加 30 分钟过期机制
- **教训**: 任何状态都要有过期或重置机制

#### 2. 时区不匹配导致 TypeError
- **问题**: 数据库时间带时区，代码时间不带时区，相减时报错
- **解决**: 统一转换为 offset-naive 时间再计算
- **教训**: 处理时间时要注意时区问题

#### 3. 关键词匹配太死板
- **问题**: 固定关键词无法覆盖所有场景，容易误判
- **解决**: LLM 优先，关键词仅作为兜底
- **教训**: 能用 LLM 解决的就不要用关键词

#### 4. 知识库无效内容干扰
- **问题**: 知识库中的空片段、"nan"值、填写说明行被搜索到，导致 LLM 返回错误回复
- **解决**: 增强内容过滤逻辑
- **教训**: 数据质量是基础，必须先清洗数据

#### 5. 评价提示太"贴脸"
- **问题**: 回答完问题立刻问评价，用户体验差
- **解决**: 改为用户表示满意/感谢时自然触发
- **教训**: 要考虑用户感受，不要过度打扰

---

## 关键修复记录（2026-04-04 新增）

### 2026-04-05: 兜底流程三大问题修复
**问题描述**:
1. 槽位状态不一致：明明已显示车牌号，但总结却说"尚未提供车牌号"
2. 退出意图检测后返回空响应
3. 确认同义词"行"返回空响应

**解决方案**:
1. **槽位状态不一致修复**：
   - 完全不使用 Summary Agent 生成的问题总结
   - 改用 `entry_problem` 或 `problem_summary` 作为基础
   - 只进行简单的"用户"到"您"的替换
   - 避免 LLM 输出不稳定导致的状态矛盾

2. **退出意图空响应修复**：
   - 在 `clear_fallback_state_node.py` 中添加退出意图检测逻辑
   - 当用户说"算了"、"不用了"等关键词时，返回友好回复
   - 在 `state.py` 的 `ClearFallbackStateOutput` 中已有 `reply_content` 字段

3. **确认回复保留修复**：
   - 修改 `CreateCaseInput` 和 `CreateCaseOutput` 添加 `reply_content` 字段
   - 修改 `EmailSendingInput` 添加 `reply_content` 字段
   - 确保后续节点能够保留和传递回复内容

**修改文件**:
- `src/graphs/nodes/fallback_node.py` - 彻底修复槽位状态问题，移除 Summary Agent 依赖
- `src/graphs/state.py` - CreateCaseInput/Output、EmailSendingInput 添加 reply_content 字段
- `src/graphs/nodes/create_case_node.py` - 保留和传递 reply_content
- `src/graphs/nodes/clear_fallback_state_node.py` - 已有退出意图检测逻辑（无需修改）

### 2026-04-04: 兜底流程状态过期机制 + 时区问题修复
**问题描述**:
1. 兜底流程状态没有过期机制，用户永久卡在兜底流程
2. 时区不匹配导致 TypeError: can't subtract offset-naive and offset-aware datetimes

**解决方案**:
1. **添加过期机制**:
   - 兜底流程状态超过 30 分钟自动重置
   - 避免用户永久卡在兜底流程

2. **修复时区问题**:
   - 统一转换为 offset-naive 时间再计算差值
   - 加 try-except 保护，时间计算出错不影响主流程

**修改文件**:
- `src/graphs/nodes/load_history_node.py` - 添加过期机制、修复时区问题

### 2026-04-04: 意图识别逻辑修复 - 用户可以正常退出兜底流程
**问题描述**:
- 在兜底流程中，除了明确的 `exit_fallback`，所有意图都被强制改成 `fallback`，导致用户无法退出

**解决方案**:
- 只有明确要继续兜底的意图才留在兜底流程
- 其他意图（使用指导、故障处理、闲聊等）正常处理，允许用户退出兜底流程

**修改文件**:
- `src/graphs/nodes/intent_recognition_node.py` - 修复意图强制修改逻辑

### 2026-04-04: 图结构重构 - 所有对话先保存到数据库
**问题描述**:
- 不是所有分支都经过 `save_history` 节点，导致部分对话没有保存
- 知识库问答不使用对话历史，AI 回复"失忆"

**解决方案**:
1. **重构图结构**:
   - 确保所有分支（评价反馈、轻度不满、满意、兜底流程）都先经过 `save_history` 节点
   - 兜底流程改为 `fallback` → `save_history` → 条件判断

2. **上下文利用**:
   - 在 `knowledge_qa_node` 中将最近 10 轮对话作为上下文传给 LLM
   - 提升回复连贯性和人情味

**修改文件**:
- `src/graphs/graph.py` - 重构图结构
- `src/graphs/nodes/knowledge_qa_node.py` - 使用对话历史作为上下文

## 工作流结构

```
load_history (加载对话历史)
        │
        ▼
intent_recognition (意图识别)
        │
        ├─ 使用指导/故障处理 → query_rewrite → knowledge_qa → save_history → save_record → END
        ├─ 兜底流程 → fallback → [创建工单/继续兜底]
        ├─ 轻度不满 → dissatisfied → save_record → END
        ├─ 满意 → satisfied → save_record → END
        ├─ 评价反馈 → feedback → save_record → END
        └─ 退出兜底 → clear_fallback_state → query_rewrite → knowledge_qa
```

## 节点清单

| 节点名 | 文件位置 | 类型 | 功能描述 | 配置文件 |
|-------|---------|------|---------|---------|
| load_history | `nodes/load_history_node.py` | task | 加载对话历史和兜底状态 | - |
| intent_recognition | `nodes/intent_recognition_node.py` | agent | 意图识别 | `config/intent_recognition_llm_cfg.json` |
| query_rewrite | `nodes/query_rewrite_node.py` | agent | 查询改写（优化搜索词） | `config/query_rewrite_llm_cfg.json` |
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
| cond_intent_recognition | `nodes/cond_intent_recognition_node.py` | condition | 意图路由 | - |
| cond_fallback | `nodes/cond_fallback_node.py` | condition | 工单确认判断 | - |
| negotiate | `nodes/negotiate_node.py` | agent | 协商处理（问清楚、给方案） | `config/negotiate_llm_cfg.json` |
| cond_negotiate | `nodes/cond_negotiate_node.py` | condition | 协商处理路由 | - |
| summary_agent | `nodes/summary_agent_node.py` | agent | Summary Agent（生成详细问题总结） | - |
| cond_after_save | `nodes/cond_after_save_node.py` | condition | save_history 后统一路由 | - |
| mark_as_save_record | `nodes/route_marker_nodes.py` | task | 标记为 save_record 路由 | - |
| mark_as_cond_fallback | `nodes/route_marker_nodes.py` | task | 标记为 cond_fallback 路由 | - |
| mark_as_cond_negotiate | `nodes/route_marker_nodes.py` | task | 标记为 cond_negotiate 路由 | - |

**类型说明**: task(普通节点) / agent(大模型节点) / condition(条件分支节点)

## 条件节点

| 节点名 | 文件位置 | 输入类型 | 功能描述 | 分支逻辑 |
|-------|---------|---------|---------|---------|
| cond_intent_recognition | `nodes/cond_intent_recognition_node.py` | IntentRouteCheck | 意图路由 | 见下表 |
| cond_fallback | `nodes/cond_fallback_node.py` | CaseConfirmedCheck | 工单确认判断 | "创建工单"→create_case, "继续兜底"→save_history |

### cond_intent_recognition 分支逻辑

| 返回值 | 目标节点 | 触发条件 |
|-------|---------|---------|
| 使用指导 | query_rewrite | intent = "usage_guidance" |
| 故障处理 | query_rewrite | intent = "fault_handling" |
| 协商处理 | negotiate | intent = "negotiate" |
| 兜底流程 | fallback | intent = "fallback" / "complaint" |
| 不满意 | dissatisfied | intent = "dissatisfied" |
| 满意 | satisfied | intent = "satisfied" |
| 评价反馈 | feedback | intent = "feedback_good" / "feedback_bad" |
| 退出兜底 | clear_fallback_state | intent = "exit_fallback" / "cancel_fallback" |

## 意图识别规则

| 意图类型 | 触发关键词/条件 |
|---------|----------------|
| usage_guidance | 使用指导类问题（默认）、问候语（你好、您好）|
| fault_handling | 充不进去、充不上、充电失败、坏了、故障等 |
| fallback | 垃圾、投诉、转人工、强烈不满 |
| dissatisfied | 没用、不行、没帮助、轻度不满 |
| satisfied | 谢谢、感谢、满意 |
| feedback_good | "1"、"很好"、"有帮助" |
| feedback_bad | "2"、"没有帮助"、"没用" |
| 闲聊（归为usage_guidance） | 天气、你是谁、无意义字符、模糊表达 |

## 兜底流程状态

| 状态值 | 含义 | 行为 |
|-------|------|------|
| `""` (空) | 不在兜底流程中 | 正常对话 |
| `"collect_info"` | 收集信息中 | 继续收集手机号/车牌号 |
| `"confirm"` | 等待用户确认 | 用户确认后 → done |
| `"done"` | 已完成 | 不保存状态，下次是新会话 |

## 兜底流程确认关键词

支持以下确认方式（模糊匹配，去掉标点后判断）：
- 精确：确认、确认无误、没问题、是的、对、好的
- 口语：确认了、对呀、是、行、可以、嗯嗯
- 带标点：确认。、确认！、是的、确认～

## 兜底流程字段说明

| 字段 | 说明 |
|------|------|
| `entry_problem` | 用户进入兜底流程时的问题描述（从对话历史中提取，排除手机号/车牌号相关消息） |
| `problem_summary` | AI 生成的问题总结 |
| `user_supplement` | 用户补充/纠正的内容 |

## 数据库设计

- `conversation_history`: 对话历史和兜底流程状态
- `dialog_records`: 有价值的对话记录（评价/不满意）
- `case_records`: 工单记录

## 技能使用

- 大语言模型：`LLMClient` (coze-coding-dev-sdk)
- 邮件发送：`integration-email-imap-smtp` 集成（QQ邮箱，端口587，STARTTLS模式）

## 邮件发送配置

| 配置项 | 值 | 配置位置 |
|-------|-----|---------|
| SMTP服务器 | smtp.qq.com | 集成管理 |
| 端口 | 587 | 集成管理 |
| 连接模式 | STARTTLS（非SSL直连） | 代码自动判断 |
| 发件邮箱 | xuefu.song@qq.com | 集成管理 |
| **收件邮箱** | xuefu.song@qq.com | 环境变量 / 配置文件 |

**注意**：
1. 端口587使用STARTTLS模式，端口465使用SSL直连模式。代码会自动根据端口选择正确的连接方式。

### 如何修改客服收件邮箱

**方式一：环境变量（推荐，线上环境）**

在平台的「环境变量」配置中添加：

| 环境变量名 | 说明 | 示例值 |
|-----------|------|--------|
| `EMAIL_RECIPIENT` | 客服收件邮箱 | `service@example.com` |
| `EMAIL_RECIPIENT_NAME` | 收件人名称（可选） | `客服团队` |

**方式二：配置文件（开发环境）**

修改 `config/email_config.json`：

```json
{
  "recipient_email": "service@example.com",
  "recipient_name": "客服团队"
}
```

**优先级**：环境变量 > 配置文件 > 默认值
- 知识库：`KnowledgeClient` (coze-coding-dev-sdk)
- 邮件发送：`EmailClient` (coze-coding-dev-sdk)
- 数据库：PostgreSQL

## 邮件配置

收件邮箱：xuefu.song@qq.com

## 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 测试用例 v2.2 | `docs/测试用例_v2.2.md` | 最新测试用例（推荐使用）⭐ |
| 测试用例 v2.1 | `docs/测试用例_v2.1.md` | 旧版测试用例 |
| 测试用例 v2.0 | `docs/测试用例_v2.0.md` | 旧版测试用例 |
| 测试用例 v1.2 | `docs/测试用例_v1.2.md` | 旧版测试用例 |
| 测试用例 | `docs/TEST_CASES.md` | 旧版测试用例 |

## 关键修复记录

### 2026-04-04: 兜底流程重构 - 简单直接，要改就改
**需求背景**：
- 用户反馈之前的流程太死板：必须按顺序（先手机号、后车牌号、最后问题）
- 用户要求更正时，系统无法回滚，必须从头开始
- 话术繁琐，车轱辘话说来说去

**解决方案**：
1. **简化流程**：
   - 用户说什么就记什么（手机号/车牌号/问题描述随意顺序）
   - 用户要改什么就直接改，不用从头开始
   - 最后让用户确认即可提交

2. **新流程**：
   - 进入兜底 → 直接询问手机号、车牌号、问题
   - 用户随意提供信息，系统随时记录
   - 用户要更正 → 直接更新，不用重来
   - 用户说"确认" → 提交工单

3. **移除复杂逻辑**：
   - 移除 phase="ask_problem" / "collect_info" / "confirm" 的死板阶段
   - 移除复杂的意图判断逻辑（announce_correction / actual_correction）
   - 只保留简单的确认和取消判断

**修改文件**：
- `src/graphs/nodes/fallback_node.py` - 完全重构，简化逻辑

**测试效果**：
| 场景 | 测试结果 |
|-----|---------|
| 用户说"我要投诉，充电桩坏了" | ✅ 记录问题 |
| 用户说"手机13812345678 车牌沪A12345" | ✅ 记录手机号和车牌号 |
| 用户说"车牌号不对，应该是沪B88888" | ✅ 直接更新车牌号 |
| 用户说"确认" | ✅ 提交工单 |

### 2026-04-04: 兜底流程优化 - 对话记录截断和话术优化
**需求背景**：
- 用户反馈邮件中包含太多历史对话记录，把不同时段的投诉混在一起
- 用户反馈话术突兀："抱歉抱歉，用户抱怨...，麻烦您再报一次手机号和车牌号"显得很生硬

**解决方案**：
1. **对话记录截断**：
   - 新增 `conversation_truncate_index` 字段，记录进入兜底流程时的对话长度
   - 邮件中只展示截断后的对话（这次投诉的对话）
   - 避免历史对话干扰，提升客服阅读体验

2. **话术优化**：
   - 将"抱歉抱歉！"改为"非常抱歉给您带来不便！"
   - 移除突兀的问题总结显示
   - 添加更自然的过渡语："为了帮您更好地处理问题"
   - 保留原有逻辑：LLM 检测抱怨后自动生成道歉话术

**修改文件**：
- `src/graphs/state.py` - 添加 `conversation_truncate_index` 字段
- `src/graphs/nodes/fallback_node.py` - 话术优化、添加截断索引记录
- `src/graphs/nodes/email_sending_node.py` - 邮件只展示截断后的对话

**测试效果**：
| 场景 | 修复前 | 修复后 |
|-----|--------|--------|
| 历史对话 | 全部展示，可能混在一起 | 只展示这次投诉的对话 ✅ |
| 抱怨话术 | "抱歉抱歉！..." | "非常抱歉给您带来不便！..." ✅ |

### 2026-04-03: 关键词匹配全面智能化 - 移除固定关键词，改用 LLM 判断
**需求背景**：
- 关键词匹配逻辑太死板，难以覆盖所有 corner case
- "谢谢你的帮助" 会被错误改写为 "谢谢你的帮助 谢谢 感谢"
- 故障关键词无法穷举，导致遗漏

**解决方案**：
1. **query_rewrite_node.py 优化**：
   - 移除 16 个固定关键词（skip_rewrite_keywords）
   - 使用 `_should_rewrite_query` 函数，通过 LLM 智能判断是否需要改写
   - 防止误判："谢谢你的帮助"不会被改写

2. **clear_fallback_state_node.py 优化**：
   - 移除 10 个固定关键词（fault_keywords）
   - 使用 `_recognize_intent_for_exit` 函数，通过 LLM 智能判断用户意图
   - 保留关键词匹配作为兜底机制

**测试效果**：
| 用户消息 | 优化前 | 优化后 |
|---------|--------|--------|
| "你好" | 关键词匹配，可能误判 | LLM 智能判断 ✅ |
| "谢谢你的帮助" | 会被改写为"谢谢你的帮助 谢谢 感谢" | **不被改写** ✅ |
| "充电桩充不进去电" | 关键词匹配，可能遗漏 | LLM 智能识别为故障 ✅ |

**修改文件**：
- `src/graphs/nodes/query_rewrite_node.py` - 使用 LLM 判断是否需要改写
- `src/graphs/nodes/clear_fallback_state_node.py` - 使用 LLM 判断用户意图

### 2026-04-03: Query Expansion 查询改写优化 - 提升知识库搜索效果
**需求背景**：
- 用户口语化问题搜索效果不佳，如"充不进去电怎么办？"、"打不着火"
- 需要提升知识库匹配率，减少"没有资料"的情况

**解决方案**：
1. **新增查询改写节点** (`query_rewrite_node`)：
   - 使用 LLM 将用户口语化问题改写为更精准的搜索词
   - 根据意图类型添加相关关键词：
     - 使用指导类：添加"操作"、"步骤"、"方法"等
     - 故障处理类：添加"故障"、"检查"、"解决"等

2. **知识库数据集迁移**：
   - 旧数据集 `charging_station_kb` 存在重复数据
   - 新数据集 `charging_station_kb_v3`：105 条独立知识库条目
   - 代码中配置 `KNOWLEDGE_TABLE_NAMES = ["charging_station_kb_v3"]`

3. **搜索参数优化**：
   - `min_score`: 0.4（降低阈值，避免错过相关内容）
   - `top_k`: 10（增加返回数量）

**测试效果**：
| 用户问题 | 改写后搜索词 | 匹配效果 |
|---------|-------------|---------|
| 充不进去电怎么办？ | 充不进去电 充不上 无法充电 故障 检查 简短回答 | ✅ 精准匹配 |
| 打不着火 | 打不着火 启动 故障 检查 简短回答 | ✅ 找到相关内容 |

**修改文件**：
- `src/graphs/nodes/query_rewrite_node.py` - 新增查询改写节点
- `src/graphs/nodes/knowledge_qa_node.py` - 添加数据集配置、修复去重逻辑、修复有效答案判断
- `config/query_rewrite_llm_cfg.json` - 查询改写 LLM 配置
- `scripts/upload_knowledge.py` - 使用新数据集名称

**关键修复**：
1. **去重逻辑优化**：第二次搜索返回相同内容但更高得分时，更新得分而非跳过
2. **有效答案判断修复**：将 `**简短回答**` 检查移到 `####` 检查之前，避免比亚迪等条目被误判为"纯标题"

### 2026-04-03: 知识库搜索参数优化 - 解决答案片段无法返回的问题
**问题描述**：
- 用户问"如何成为会员享受优惠？"返回"没有资料"
- 但知识库中确实有答案片段：`**简短回答**：在App注册账号即为普通会员...`

**根本原因**：
- 知识库搜索参数 `top_k=5, min_score=0.5` 导致只返回 1 条结果（只有标题片段）
- 答案片段得分 0.546 > 0.5，但搜索只返回了标题片段（得分 0.95）

**解决方案**：
- 降低 `min_score` 从 0.5 到 0.4
- 增加 `top_k` 从 5 到 10
- 确保搜索能返回更多结果，包括答案片段

**测试效果**：
| 用户问题 | 修复前 | 修复后 |
|---------|--------|--------|
| 如何成为会员享受优惠？ | ❌ 没有资料 | ✅ 在App注册账号即为普通会员... |
| 充电的费用是怎么算的？ | ❌ 没有资料 | ✅ 部分站点按充电时长计费... |
| 直流快充和交流慢充有什么区别？ | ❌ 没有资料 | ✅ 直流快充功率大速度快... |

**修改文件**：
- `src/graphs/nodes/knowledge_qa_node.py` - 调整搜索参数

### 2026-04-03: 知识库内容过滤优化 - 支持更多有效内容格式
**问题描述**：
- 用户问"充电的费用是怎么算的？"、"直流快充和交流慢充有什么区别？"都返回"没有资料"
- 但知识库里明明有相关内容

**根本原因**：
- 之前的过滤逻辑只接受包含"简短回答"关键词的内容
- 知识库中的片段格式多样（如 `1. 按充电电量计费`、`- **快充桩**：30-60分钟`）被错误过滤

**解决方案**：
- 扩展有效内容识别规则，支持：
  - 编号列表：`1. xxx`、`2. xxx`
  - 列表项：`- **xxx**`
  - 时间范围：`4-8小时`、`30-60分钟`
  - 费用信息：`元/度`、`按...计费`
  - 加粗标签：`**xxx**：`

**测试效果**：
| 用户问题 | 修复前 | 修复后 |
|---------|--------|--------|
| 充电的费用是怎么算的？ | ❌ 暂时没有资料 | ✅ 部分站点按充电时长计费... |
| 直流快充和交流慢充有什么区别？ | ❌ 暂时没有资料 | ✅ 直流快充30-60分钟可充至80%... |

**修改文件**：
- `src/graphs/nodes/knowledge_qa_node.py` - 扩展有效内容识别规则

### 2026-04-03: 知识库搜索结果过滤优化 - 无效内容不再传递给 LLM
**问题描述**：
- 用户问很多问题都返回"不好意思，这个问题我这边暂时没有资料"
- 但知识库里明明有相关内容

**根本原因**：
- 知识库搜索返回的结果可能只是标题或空片段（如 `**详细回答**：`）
- 之前的代码会把这些无效内容传给 LLM
- LLM 拿到无效内容无法理解，只能返回"没有资料"

**解决方案**：
1. 当所有搜索结果都是无效内容时，返回空内容给 LLM
2. LLM 按照"知识库为空"规则，友好引导用户描述具体问题
3. 更新 LLM 配置，优化无内容时的回复话术

**测试效果**：
| 用户问题 | 修复前 | 修复后 |
|---------|--------|--------|
| 你好 | ❌ 抱歉，我现在有点忙 | ✅ 友好引导 |
| 充电桩充不进去电 | ❌ 暂时没有资料 | ✅ 检查充电口是否有异物... |
| 比亚迪充电桩怎么扫码 | ❌ 暂时没有资料 | ✅ 充电桩侧面或顶部... |

**修改文件**：
- `src/graphs/nodes/knowledge_qa_node.py` - 无效内容过滤后返回空
- `config/knowledge_qa_llm_cfg.json` - 优化无内容回复话术

### 2026-04-02: 修复"你好"返回错误回复问题
**问题描述**：
- 用户发送"你好"问候语，系统返回"抱歉，我现在有点忙，请稍后再试"
- 用户体验差，问候语无法得到正确回应

**根本原因**：
- 知识库中存在无效数据：
  1. 旧文档的空片段（如"**详细回答**："后面没有实际内容）
  2. Excel 末尾的填写说明行被错误导入
  3. Excel 空单元格被导入为 "nan" 字符串
- 知识库搜索匹配到这些无效内容，导致 LLM 返回错误回复

**解决方案**：
- 增强 `_is_valid_answer_content` 函数，过滤无效内容：
  1. 过滤 "nan" 值（Excel 空单元格导入）
  2. 过滤空片段（只有标题没有实际内容）
  3. 过滤填写说明/注释（Excel 末尾的说明行）

**测试效果**：
| 用户消息 | 修复前 | 修复后 |
|---------|--------|--------|
| 你好 | 抱歉，我现在有点忙 | 您好呀😊！我是充电桩客服小助手... |
| 特斯拉充电桩怎么扫码 | 正常 | 正常 |

**修改文件**：
- `src/graphs/nodes/knowledge_qa_node.py` - 增强内容过滤逻辑

### 2026-04-02: 邮件添加完整对话记录
**需求背景**：
- 客服人员反馈邮件中缺少对话上下文
- 无法了解用户之前和 AI 的完整交互过程

**解决方案**：
- EmailSendingInput 添加 conversation_history 字段
- 邮件正文新增"完整对话记录"部分，包含用户和 AI 的所有对话
- 对话记录采用可滚动设计，最大高度 400px，避免邮件过长

**邮件结构**：
1. 工单编号
2. 手机号
3. 车牌号
4. 问题总结
5. **完整对话记录**（新增）

**修改文件**：
- `src/graphs/state.py` - EmailSendingInput 添加 conversation_history
- `src/graphs/nodes/email_sending_node.py` - 邮件正文添加对话记录

### 2026-04-02: 评价提示时机优化 - 不再"贴脸"问评价
**问题描述**：
- 用户问"充电桩选哪一个"，系统回答后立刻弹出评价提示
- 用户体验差，评价来得太突兀，像是在"逼问"

**用户反馈**：
> "你可能没理解我的诉求...他回答完了之后，用户又没说什么'谢谢'、'你好'之类的，他就直接抛出来让用户回答了...这个要评价的环节，实在是要得有点太'贴脸'了"

**解决方案**：
- 知识库问答节点不再主动请求评价（should_ask_feedback 始终返回 false）
- 评价改为在用户表示满意/感谢时自然触发
- 流程：回答问题 → 用户说"谢谢" → 显示评价选项

**修复后的对话流程**：
| 轮次 | 用户 | 系统 |
|------|------|------|
| 1 | 特斯拉充电桩怎么扫码？ | 充电桩正面显示屏下方，有黑白二维码...（无评价） |
| 2 | 谢谢 | 不客气！... 请问这个回答对您有帮助吗？ |

**修改文件**：
- `config/knowledge_qa_llm_cfg.json` - 移除主动请求评价逻辑

### 2026-04-02: 评价触发逻辑优化 - 知识库得分 + 内容质量双重判断
**问题描述**：
- 用户问"充电桩选哪一个"，知识库返回片段"选择高功率充电桩"（得分 0.67）
- LLM 错误判断 should_ask_feedback = true，触发了评价提示
- 但实际这个回答质量不高，不应该触发评价

**根本原因**：
- 之前 LLM 只根据"是否有知识库内容"判断是否请求评价
- 没有考虑知识库得分和内容质量

**解决方案**：
1. **传递知识库得分给 LLM**：
   - 修改 `_search_knowledge_with_retry` 返回 best_score
   - 在用户提示词中添加 `knowledge_score` 变量

2. **优化评价判断规则**：
   - 知识库得分 >= 0.70 且内容是完整答案 → 请求评价
   - 知识库得分 < 0.70 或内容只是片段 → 不请求评价
   - 完整答案特征：包含"简短回答"关键词、或具体操作指引

**测试效果**：
| 用户问题 | 知识库得分 | 内容类型 | 评价触发 |
|---------|-----------|---------|---------|
| 特斯拉怎么扫码 | 0.735 | 完整答案 | ✅ 是 |
| 充电桩选哪一个 | 0.67 | 片段 | ❌ 否 |

**修改文件**：
- `src/graphs/nodes/knowledge_qa_node.py` - 返回知识库得分，传递给 LLM
- `config/knowledge_qa_llm_cfg.json` - 优化评价判断规则

### 2026-04-02: 优化兜底流程确认逻辑和语音输入处理
**问题描述**：
1. 确认关键词精确匹配，用户说"确认。"或"确认了"无法识别
2. 语音输入格式复杂，如"手机号139。16425678。车牌号。沪a Dr 3509."
3. 收集信息的话术比较死板，不够自然

**解决方案**：
1. **确认逻辑改为模糊匹配**：
   - 去掉标点符号后匹配
   - 支持"确认。"、"确认了"、"是"、"对呀"等

2. **增强 LLM 提取信息的提示词**：
   - 添加示例，处理分段语音输入
   - 提取规则更清晰

3. **优化回复话术**：
   - 旧："请提供您的手机号："
   - 新："方便提供一下您的手机号和车牌号吗？"

**修改文件**：
- `src/graphs/nodes/fallback_node.py` - 确认逻辑、LLM 提取提示词、回复话术

### 2026-04-02: 新增"闲聊"意图类型，提升用户体验
**问题背景**：
- 用户可能发送闲聊、无意义字符、模糊问题等
- 之前这类消息会被误判为某个意图，导致奇怪回复

**解决方案**：
1. **意图识别新增"闲聊"类型**：
   - 天气、你是谁、开玩笑 → 闲聊
   - 无意义字符（asdfgh、...、嗯、哦）→ 闲聊
   - 模糊表达（帮我、问题）且无法确定 → 闲聊

2. **知识库问答优化回复话术**：
   - 闲聊类：幽默回应，引导到充电话题
   - 无意义：友好提示，引导说出具体需求
   - 模糊问题：询问用户具体遇到什么问题

**测试效果**：
| 用户消息 | 回复示例 |
|---------|---------|
| 今天天气怎么样 | "哈哈，我是个充电桩客服，看不了天气呢～..." |
| 你是真人吗 | "我是充电桩小助手，虽然不是真人，但我会尽全力帮您..." |
| asdfgh | "不好意思，我没看懂您的输入呢～您能跟我说说具体遇到了什么情况吗？" |

**修改文件**：
- `config/intent_recognition_llm_cfg.json` - 新增闲聊类型
- `config/knowledge_qa_llm_cfg.json` - 优化闲聊回复话术

### 2026-04-02: 问候语误判为投诉兜底
**问题描述**：
- 用户说"你好"被 LLM 误判为"投诉兜底"，直接进入兜底流程

**根本原因**：
- 提示词中没有定义"问候语"类型
- LLM 不知道如何处理"你好"，随机选择了一个意图

**解决方案**：
1. **更新提示词**：
   - 添加"问候"类型：你好、您好、在吗、有人在吗
   - 明确问候语归为"使用指导"类，引导用户提问
   - 强调只有明确不满/投诉/转人工才判断为投诉兜底

2. **更新意图映射逻辑**：
   - 添加对"问候"类型的判断，映射为 `usage_guidance`

**修改文件**：
- `config/intent_recognition_llm_cfg.json` - 更新提示词
- `src/graphs/nodes/intent_recognition_node.py` - 添加问候类型映射

**测试结果**：
- ✅ "你好" → 使用指导（引导用户提问）
- ✅ "我要投诉" → 兜底流程
- ✅ "特斯拉怎么充电" → 使用指导

### 2026-04-02: 意图识别重构 - LLM 优先
**问题描述**：
- 用户在兜底流程 confirm 阶段纠正问题总结时，消息包含"如何"被误判为"问新问题"
- 系统错误退出兜底流程，导致用户投诉无法正常提交

**根本原因**：
- 意图识别使用大量正则/关键词匹配，LLM 仅作为兜底
- 正则无法理解语义，导致各种边界情况误判

**解决方案**：
1. **重构意图识别节点**：
   - 移除复杂的正则判断逻辑
   - LLM 优先，传入兜底流程上下文（fallback_phase、problem_summary、entry_problem）
   - 数字评价（1/2）保持快速判断，不调用 LLM

2. **简化兜底退出逻辑**：
   - 只有用户明确说"取消"、"不需要了"才退出兜底
   - 其他情况默认继续兜底流程

3. **更新 LLM 配置文件**：
   - 完善意图类型定义
   - 明确兜底流程中的判断规则

**修改文件**：
- `src/graphs/nodes/intent_recognition_node.py` - 重构为 LLM 优先
- `src/graphs/state.py` - IntentRecognitionInput 添加兜底上下文字段
- `config/intent_recognition_llm_cfg.json` - 更新提示词

**测试结果**：
- ✅ 用户纠正问题总结 → 继续兜底，更新问题总结
- ✅ 用户明确取消 → 退出兜底
- ✅ 用户确认 → 完成兜底流程

### 2026-04-01: 测试用例全面更新
**更新内容**：
- 新增 15 个完整测试用例，覆盖所有功能场景
- 添加数据库验证 SQL 查询
- 添加测试报告模板
- 添加测试数据参考

**文件位置**：`docs/测试用例_v2.0.md`

### 2026-04-01: 评价选项格式和知识库问答评价判断修复
**问题描述**：
1. 评价选项格式不规范（原为 emoji 形式）
2. 知识库问答后评价提示不显示（LLM 未返回 should_ask_feedback 字段）
3. 确认关键词不够完善（缺少"没其他问题了"等）

**解决方案**：
1. **评价选项改为数字格式**：
   - satisfied_node.py: "1. 有帮助  2. 没有帮助"
   - knowledge_qa_node.py: 同步修改

2. **知识库问答评价判断优化**：
   - config/knowledge_qa_llm_cfg.json: 添加 should_ask_feedback 字段说明
   - knowledge_qa_node.py: 处理 LLM 返回的 should_ask_feedback 字段

3. **确认关键词完善**：
   - intent_recognition_node.py: 添加"没其他问题了"、"没事了"、"没问题了"等
   - fallback_node.py: 同步更新确认关键词

4. **配置文件修复**：
   - 删除 config/email_config.json（被系统误判为大模型配置文件）
   - 邮件收件配置通过环境变量或代码默认值支持

**修改文件**：
- `src/graphs/nodes/satisfied_node.py` - 评价选项改为数字格式
- `src/graphs/nodes/knowledge_qa_node.py` - 处理 should_ask_feedback 字段
- `config/knowledge_qa_llm_cfg.json` - 添加 should_ask_feedback 字段
- `src/graphs/nodes/intent_recognition_node.py` - 完善确认关键词
- `src/graphs/nodes/fallback_node.py` - 同步确认关键词

### 2025-01-XX: 确认流程和评价方式优化
**问题描述**：
1. 用户回复"准确"后，被误判为"满意"而不是确认
2. 确认后的回复话术需要调整
3. 评价方式改为数字选项

**解决方案**：
1. **确认关键词扩展**：
   - intent_recognition_node.py: 添加"准确"、"可以"、"行"到确认关键词
   - fallback_node.py: 同步添加确认关键词

2. **回复话术调整**：
   - 确认后回复："收到您的问题，我们的工作人员将会尽快处理，并在1-3个工作日内联系您。"
   - 邮件发送成功后也使用相同话术

3. **评价方式改为数字**：
   - 1. 有帮助
   - 2. 没有帮助

4. **entry_problem 提取逻辑优化**：
   - 优先使用当前用户消息作为问题描述
   - 只有当前消息不包含实际问题时，才从历史中查找

**修改文件**：
- `src/graphs/nodes/intent_recognition_node.py` - 扩展确认关键词
- `src/graphs/nodes/fallback_node.py` - 同步确认关键词，优化 entry_problem 提取逻辑
- `src/graphs/nodes/email_sending_node.py` - 修改回复话术
- `src/graphs/nodes/knowledge_qa_node.py` - 修改评价方式为数字

### 2025-01-XX: 数据库缺少 entry_problem 列导致状态丢失
**问题描述**：
- 所有 Supabase 请求返回 400 Bad Request
- 问题总结不准确，总是显示"充电桩相关问题"
- 用户纠正问题总结时无法正确更新

**根本原因**：
- 数据库表 `conversation_history` 缺少 `entry_problem` 列
- 查询和插入操作都请求了不存在的列，导致 400 错误
- 状态无法保存/加载，导致 `entry_problem` 始终为空

**解决方案**：
- 执行 SQL：`ALTER TABLE conversation_history ADD COLUMN entry_problem TEXT;`
- 添加详细的错误日志便于排查问题

**修改文件**：
- `src/graphs/nodes/load_history_node.py` - 添加错误日志
- `src/graphs/nodes/save_history_node.py` - 添加错误日志
