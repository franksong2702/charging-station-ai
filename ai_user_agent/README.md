# AI 用户智能体 (AI User Agent)

用于测试充电桩客服 AI 的智能用户模拟器，支持多种用户角色和对话场景。

## 📋 功能特性

- ✅ **6 种测试场景**：标准投诉、情绪激动、逐步提供、纠正型、中途退出、确认词测试
- ✅ **角色扮演**：模拟不同性格的真实用户
- ✅ **多轮对话**：支持连续对话，保持上下文连贯
- ✅ **REST API**：提供 HTTP 接口，方便集成
- ✅ **会话管理**：支持多会话并发，自动管理对话历史
- ✅ **易于调试**：详细日志和错误处理

## 🚀 快速开始

### 1. 安装依赖

```bash
cd ai_user_agent
pip install -r requirements.txt
```

### 2. 配置模型

编辑 `config.json`，设置模型参数：

```json
{
  "model": "doubao-seed-1-8-251228",
  "temperature": 0.8,
  "max_tokens": 2000
}
```

### 3. 启动 API 服务

```bash
python api.py
```

服务将在 `http://localhost:8000` 启动。

### 4. 访问 API 文档

打开浏览器访问：`http://localhost:8000/docs`

## 📖 API 使用说明

### 1. 获取所有场景

```bash
GET http://localhost:8000/scenarios
```

**响应：**
```json
[
  {
    "type": "standard_complaint",
    "name": "标准投诉用户",
    "description": "配合型用户，主动提供完整信息"
  },
  ...
]
```

### 2. 发起对话

#### 第一次对话（开始新对话）

```bash
POST http://localhost:8000/chat
Content-Type: application/json

{
  "scenario_type": "standard_complaint",
  "session_id": "session_001"
}
```

**响应：**
```json
{
  "user_reply": "你好，我遇到充电异常扣费问题了",
  "is_end": false,
  "current_stage": "describing_problem",
  "scenario_type": "standard_complaint"
}
```

#### 多轮对话（继续对话）

```bash
POST http://localhost:8000/chat
Content-Type: application/json

{
  "scenario_type": "standard_complaint",
  "ai_assistant_reply": "您好，请问您的手机号是多少？",
  "session_id": "session_001"
}
```

**响应：**
```json
{
  "user_reply": "13800138000",
  "is_end": false,
  "current_stage": "providing_phone",
  "scenario_type": "standard_complaint"
}
```

### 3. 获取会话历史

```bash
GET http://localhost:8000/session/session_001/history
```

### 4. 重置会话

```bash
POST http://localhost:8000/session/reset
Content-Type: application/json

{
  "session_id": "session_001"
}
```

## 🎭 测试场景说明

### 1. standard_complaint（标准投诉用户）
- **特点**：配合型，主动提供完整信息
- **用途**：测试标准投诉流程
- **预期行为**：友好回答，一次性提供信息

### 2. angry_user（情绪激动用户）
- **特点**：愤怒，不配合，需要安抚
- **用途**：测试客服情绪安抚能力
- **预期行为**：抱怨，语气激动，需要客服耐心

### 3. gradual_info（逐步提供信息用户）
- **特点**：耐心，信息分批提供
- **用途**：测试多轮信息收集
- **预期行为**：一次只提供一条信息

### 4. corrective（纠正型用户）
- **特点**：较真，会纠正 AI 的错误
- **用途**：测试 AI 信息准确性
- **预期行为**：发现错误立即纠正

### 5. early_exit（中途退出用户）
- **特点**：不耐烦，对话中途放弃
- **用途**：测试快速响应能力
- **预期行为**：5 轮内不解决就放弃

### 6. confirm_synonyms（确认词测试用户）
- **特点**：配合，使用不同确认词
- **用途**：测试确认词识别
- **预期行为**：轮换使用"对、是的、好的、行"等

## 💻 代码示例

### Python 调用示例

```python
import requests

# API 地址
BASE_URL = "http://localhost:8000"

# 1. 获取场景列表
scenarios = requests.get(f"{BASE_URL}/scenarios").json()
print("可用场景:", scenarios)

# 2. 发起对话
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "scenario_type": "standard_complaint",
        "session_id": "test_session"
    }
)
result = response.json()
print(f"用户：{result['user_reply']}")

# 3. 模拟客服回复后继续对话
ai_reply = "您好，请问您的手机号是多少？"
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "scenario_type": "standard_complaint",
        "ai_assistant_reply": ai_reply,
        "session_id": "test_session"
    }
)
result = response.json()
print(f"客服：{ai_reply}")
print(f"用户：{result['user_reply']}")

# 4. 检查是否结束
if result['is_end']:
    print("对话结束")
else:
    print("继续对话...")
```

### cURL 调用示例

```bash
# 发起对话
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_type": "standard_complaint",
    "session_id": "test_001"
  }'

# 继续对话
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_type": "standard_complaint",
    "ai_assistant_reply": "您好，请问您的手机号是多少？",
    "session_id": "test_001"
  }'
```

## 🧪 测试运行

直接运行测试：

```bash
python agent.py
```

这将执行一个简单的测试场景，输出对话示例。

## 📦 项目结构

```
ai_user_agent/
├── agent.py           # 核心智能体逻辑
├── api.py             # REST API 接口
├── scenarios.py       # 场景配置
├── config.json        # 模型配置
├── requirements.txt   # 依赖包
├── README.md          # 说明文档
└── git_push.sh        # Git 提交脚本
```

## 🔧 配置说明

### config.json 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| model | string | doubao-seed-1-8-251228 | 模型 ID |
| temperature | float | 0.8 | 温度参数（0-2） |
| max_tokens | int | 2000 | 最大生成 token 数 |
| top_p | float | 0.9 | 核采样参数 |
| timeout | int | 60 | 超时时间（秒） |

## 🚢 部署到 Coze

该智能体可以轻松迁移到 Coze 平台：

1. **核心逻辑**：`agent.py` 的 `AIUserAgent.chat()` 方法
2. **Prompt 配置**：`scenarios.py` 中的场景定义
3. **API 接口**：`api.py` 可作为工作流节点参考

在 Coze 上创建工作流时：
- 使用相同的大模型（豆包）
- 复制场景 Prompt 到工作流节点
- 使用相同的输入/输出格式

## 📝 输入/输出格式

### 输入格式

```json
{
  "scenario_type": "standard_complaint",  // 必填：场景类型
  "ai_assistant_reply": "客服的回复",       // 可选：客服回复（多轮对话时必填）
  "history": [                              // 可选：历史记录
    {"role": "user", "content": "用户消息"},
    {"role": "assistant", "content": "客服回复"}
  ],
  "session_id": "session_001"              // 可选：会话 ID
}
```

### 输出格式

```json
{
  "user_reply": "用户的回复内容",           // 必填：回复内容
  "is_end": false,                         // 必填：是否结束
  "current_stage": "providing_phone",      // 必填：当前阶段
  "scenario_type": "standard_complaint",   // 必填：场景类型
  "extra": {                               // 可选：额外字段
    "info_count": 1,
    "confirm_word": "对"
  }
}
```

## 🔍 常见问题

### Q1: 如何修改场景的 Prompt？

编辑 `scenarios.py`，修改对应场景的 `system_prompt` 字段。

### Q2: 如何添加新场景？

在 `scenarios.py` 的 `SCENARIOS` 字典中添加新的场景配置。

### Q3: 会话历史会保留多久？

会话历史存储在内存中，服务重启后会清空。如需持久化，需要添加数据库支持。

### Q4: 如何切换模型？

修改 `config.json` 中的 `model` 字段，或通过代码传入参数。

## 📄 License

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 联系方式

如有问题，请联系开发者。
