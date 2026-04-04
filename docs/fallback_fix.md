# 兜底流程误确认问题修复

## 问题描述

用户反映：在进入兜底流程后，系统收集了手机号、车牌号以及问题，但用户并没有点击确认，系统就发送了邮件，且邮件中缺失了手机号和车牌号。

## 根本原因分析

### 原因 1：确认判断逻辑太宽松

**修复前代码**（`src/graphs/nodes/fallback_node.py` 第 490-508 行）：

```python
# 模糊匹配：检查清理后的消息是否等于或在关键词列表中
is_confirm = cleaned_message in confirm_keywords or any(
    cleaned_message.startswith(kw) or cleaned_message == kw for kw in confirm_keywords
)
```

**问题**：使用了 `startswith` 模糊匹配，导致以下用户消息被误判为确认：
- "好的，请收集我的信息" → 匹配 "好的" → **误判为确认**
- "可以开始收集" → 匹配 "可以" → **误判为确认**
- "好的，我告诉你手机号" → 匹配 "好的" → **误判为确认**
- "行，你问吧" → 匹配 "行" → **误判为确认**

### 原因 2：工作流顺序错误

**修复前工作流**：
```
fallback (case_confirmed=True)
  → create_case
  → clear_fallback_state  ← 清空 phone、license_plate
  → email_sending         ← 收到空值！
```

**问题**：`clear_fallback_state_node` 会清空所有兜底状态字段，导致 `email_sending_node` 收到的是空值。

### 原因 3：清除兜底状态后的路由判断缺失

**修复前代码**（`src/graphs/graph.py`）：
```python
builder.add_edge("clear_fallback_state", END)
builder.add_edge("clear_fallback_state", "query_rewrite")  # 冲突！
```

**问题**：两条固定边冲突，无法区分"工单完成后退出"和"用户主动退出兜底"两种场景。

---

## 修复方案

### 修复 1：确认判断改为精确匹配

**文件**：`src/graphs/nodes/fallback_node.py`

**修改后代码**：
```python
# 清理用户消息（去掉标点符号和空格，用于精确匹配）
cleaned_message = user_message.strip()
for char in "，。！？、；：""''！？.,;:!? ":
    cleaned_message = cleaned_message.replace(char, "")

# 精确匹配：只认可明确的确认语句
confirm_keywords = [
    "确认", "确认无误", "没问题", "确认无误", "正确", "没错",
    "准确", "OK", "ok", "对的", "确认了", "确认呀", "没问题了",
    "没其他问题", "没其他问题了", "没有其他问题", "没有其他问题了",
    "就这样", "可以了", "好的没问题", "是对的", "确认正确"
]
is_confirm = cleaned_message in confirm_keywords  # 精确匹配
```

**测试对比**：

| 用户消息 | 修复前 | 修复后 |
|---------|-------|-------|
| 好的，请收集我的信息 | ✗ 误判为确认 | ✓ 正确判断为非确认 |
| 可以开始收集 | ✗ 误判为确认 | ✓ 正确判断为非确认 |
| 好的，我告诉你手机号 | ✗ 误判为确认 | ✓ 正确判断为非确认 |
| 确认 | ✓ 判断为确认 | ✓ 判断为确认 |
| 没问题 | ✓ 判断为确认 | ✓ 判断为确认 |
| 可以了 | ✓ 判断为确认 | ✓ 判断为确认 |

---

### 修复 2：调整工作流顺序

**文件**：`src/graphs/graph.py`

**修改前**：
```python
builder.add_edge("create_case", "clear_fallback_state")
builder.add_edge("clear_fallback_state", "email_sending")
```

**修改后**：
```python
# 创建工单 → 邮件发送 → 清除兜底状态 → 结束
# 注意：必须先发送邮件，再清除状态，因为邮件发送需要手机号、车牌号等数据
builder.add_edge("create_case", "email_sending")
builder.add_edge("email_sending", "clear_fallback_state")
builder.add_edge("clear_fallback_state", END)
```

---

### 修复 3：添加条件路由判断

**文件 1**：`src/graphs/nodes/cond_fallback_node.py`

添加新的条件判断函数：
```python
class ClearFallbackStateRouteCheck(BaseModel):
    """清除兜底状态后的路由检查输入"""
    user_message: str = Field(default="", description="用户消息")
    case_confirmed: bool = Field(default=False, description="是否已确认工单")


class ClearFallbackRouteOutput(BaseModel):
    """清除兜底状态后的路由输出"""
    route: str = Field(..., description="路由结果")


def cond_clear_fallback_state_route_path(state: ClearFallbackStateRouteCheck) -> str:
    """用于 add_conditional_edges 的路径函数"""
    if state.case_confirmed:
        return "end"
    else:
        return "query_rewrite"
```

**文件 2**：`src/graphs/graph.py`

```python
# 清除兜底状态后的路由判断
builder.add_conditional_edges(
    source="clear_fallback_state",
    path=cond_clear_fallback_state_route_path,
    path_map={
        "end": END,
        "query_rewrite": "query_rewrite"
    }
)
```

**文件 3**：`src/graphs/state.py`

添加 `case_confirmed` 字段到 `ClearFallbackStateInput`：
```python
class ClearFallbackStateInput(BaseModel):
    """清除兜底状态节点的输入"""
    user_id: str = Field(default="", description="用户身份标识")
    user_message: str = Field(default="", description="用户消息")
    reply_content: str = Field(default="", description="AI 回复内容")
    case_confirmed: bool = Field(default=False, description="是否已确认工单（用于路由判断）")
```

**文件 4**：`src/graphs/nodes/clear_fallback_state_node.py`

保留 `case_confirmed` 值用于路由判断：
```python
# 保存传入的 case_confirmed 值（用于路由判断）
was_case_confirmed = state.case_confirmed

return ClearFallbackStateOutput(
    ...
    case_confirmed=was_case_confirmed,  # 保留原值，用于路由判断
    ...
)
```

---

## 修复后工作流程

### 场景 1：用户确认工单
```
1. fallback (用户说"确认") → case_confirmed=True
2. create_case → 创建工单
3. email_sending → 发送邮件（包含手机号、车牌号）✓
4. clear_fallback_state → 清除状态
5. END (case_confirmed=True → end) ✓
```

### 场景 2：用户退出兜底
```
1. fallback (用户说"取消兜底") → 退出
2. intent_recognition → 退出兜底
3. clear_fallback_state → 清除状态
4. query_rewrite (case_confirmed=False → query_rewrite) ✓
5. knowledge_qa → 继续处理用户问题
```

### 场景 3：用户说"好的，收集信息"（未确认）
```
1. fallback (用户说"好的，收集信息") → case_confirmed=False ✓
   （修复前会误判为确认）
2. save_history → 保存对话
3. END
```

---

## 验证步骤

1. **本地测试**：运行 `python debug_fallback.py` 验证兜底流程状态处理
2. **单元测试**：运行 `python src/tests/test_fallback_fix.py` 验证修复逻辑
3. **部署测试**：部署到 Coze 平台，测试以下场景：
   - 用户完成兜底流程并确认 → 邮件应包含手机号、车牌号
   - 用户说"好的，收集信息" → 不应创建工单
   - 用户说"取消兜底" → 应退出兜底并继续回答问题

---

## 修改文件列表

1. `src/graphs/nodes/fallback_node.py` - 修复确认判断逻辑
2. `src/graphs/graph.py` - 调整工作流顺序，添加条件路由
3. `src/graphs/state.py` - 添加 case_confirmed 字段到 ClearFallbackStateInput
4. `src/graphs/nodes/cond_fallback_node.py` - 添加条件路由判断函数
5. `src/graphs/nodes/clear_fallback_state_node.py` - 保留 case_confirmed 值

---

## 下一步

1. 将修复合并到 dev 分支
2. 部署到 Coze 平台
3. 监控线上日志，确认修复效果
