# 充电桩智能客服 API 集成文档

> **文档版本**：v1.0  
> **最后更新**：2026年3月  
> **适用对象**：腾讯云函数开发者、后端开发工程师

---

## 一、概述

本文档描述了充电桩智能客服工作流的API接口规范，供腾讯云函数或其他后端服务集成调用。

### 1.1 功能说明

充电桩智能客服提供以下能力：

| 功能 | 说明 |
|------|------|
| **意图识别** | 自动识别用户问题类型（使用指导/故障处理/投诉兜底） |
| **知识库问答** | 基于充电桩知识库回答用户问题 |
| **信息收集** | 提取用户投诉信息（手机号、订单号等） |
| **邮件通知** | 将投诉信息发送到客服邮箱 |

### 1.2 调用流程

```
腾讯云函数
    ↓ HTTP POST
AI工作流API
    ↓ 处理用户消息
返回回复内容
```

---

## 二、API 接口规范

### 2.1 基本信息

| 项目 | 说明 |
|------|------|
| **接口地址** | `http://<服务器地址>:5000/run` |
| **请求方法** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | 无（当前版本无需认证） |
| **超时建议** | 30秒 |

### 2.2 请求参数

#### 请求头（Headers）

```
Content-Type: application/json
```

#### 请求体（Body）

| 参数名 | 类型 | 必填 | 说明 | 示例值 |
|--------|------|------|------|--------|
| `user_message` | string | ✅ 是 | 用户发送的消息内容 | `"充电停不下来了怎么办？"` |

#### 请求示例

```json
{
  "user_message": "我看到充电桩上有很多二维码，不知道应该扫哪一个？我是特斯拉的车。"
}
```

### 2.3 响应参数

#### 成功响应（HTTP 200）

| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `reply_content` | string | AI客服的回复内容 | `"您好！如果您是特斯拉车辆..."` |
| `run_id` | string | 本次运行的唯一标识（用于追踪和取消） | `"383b7167-7f34-4346-8020-ee274fd3d710"` |

#### 响应示例

```json
{
  "reply_content": "您好！如果您是特斯拉车辆，请查看充电桩正面显示屏下方，找到黑白二维码（旁边有Tesla标识），使用微信或小程序扫码即可开始充电。",
  "run_id": "383b7167-7f34-4346-8020-ee274fd3d710"
}
```

### 2.4 错误响应

#### 400 错误（参数错误）

```json
{
  "detail": "Invalid JSON format"
}
```

#### 500 错误（服务器内部错误）

```json
{
  "detail": {
    "error_code": "INTERNAL_ERROR",
    "error_message": "服务器内部错误",
    "stack_trace": "..."
  }
}
```

#### 504 错误（超时）

```json
{
  "status": "timeout",
  "run_id": "xxx-xxx-xxx",
  "message": "Execution timeout: exceeded 900 seconds"
}
```

---

## 三、业务场景说明

### 3.1 支持的问题类型

工作流会自动识别用户问题类型并给出相应回复：

| 问题类型 | 关键词示例 | 处理方式 |
|---------|-----------|---------|
| **使用指导** | 扫码、二维码、怎么用、如何操作 | 查询知识库 → 返回操作指引 |
| **故障处理** | 停不下来、拔不出来、充不上、失败 | 查询知识库 → 返回解决方案 |
| **投诉兜底** | 退款、扣费异常、金额不对、投诉 | 收集信息 → 发送邮件 → 告知用户 |

### 3.2 响应时间

| 场景 | 平均响应时间 | 建议 |
|------|-------------|------|
| 知识库问答 | 2-5秒 | - |
| 投诉处理 | 3-8秒 | 包含邮件发送 |

---

## 四、集成代码示例

### 4.1 Python 示例（腾讯云函数）

```python
# -*- coding: utf-8 -*-
import json
import requests
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 配置：替换为实际的API地址
AI_WORKFLOW_API_URL = "http://<服务器地址>:5000/run"


def main_handler(event, context):
    """
    腾讯云函数入口
    
    Args:
        event: 触发器事件数据
        context: 运行上下文
    
    Returns:
        API网关响应格式
    """
    try:
        # 1. 解析请求
        if 'body' in event:
            body = event.get('body', '{}')
            if isinstance(body, str):
                request_data = json.loads(body)
            else:
                request_data = body
        else:
            request_data = event
        
        # 2. 提取用户消息
        user_message = request_data.get('user_message')
        if not user_message:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": False,
                    "error": "MISSING_PARAMETER",
                    "message": "缺少必填参数：user_message"
                }, ensure_ascii=False)
            }
        
        logger.info(f"收到用户消息: {user_message}")
        
        # 3. 调用AI工作流API
        response = requests.post(
            AI_WORKFLOW_API_URL,
            json={"user_message": user_message},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        # 4. 处理响应
        if response.status_code == 200:
            result = response.json()
            logger.info(f"AI回复成功: {result.get('reply_content', '')[:50]}...")
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": True,
                    "reply_content": result.get('reply_content', ''),
                    "run_id": result.get('run_id', '')
                }, ensure_ascii=False)
            }
        else:
            logger.error(f"API调用失败: {response.status_code}")
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": False,
                    "error": "API_ERROR",
                    "message": f"AI工作流调用失败: {response.status_code}",
                    "detail": response.text
                }, ensure_ascii=False)
            }
    
    except requests.Timeout:
        logger.error("API调用超时")
        return {
            "statusCode": 504,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "error": "TIMEOUT",
                "message": "API调用超时，请稍后重试"
            }, ensure_ascii=False)
        }
    
    except Exception as e:
        logger.error(f"未知异常: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "error": "INTERNAL_ERROR",
                "message": f"服务器错误: {str(e)}"
            }, ensure_ascii=False)
        }
```

### 4.2 Node.js 示例

```javascript
const axios = require('axios');

// 配置：替换为实际的API地址
const AI_WORKFLOW_API_URL = 'http://<服务器地址>:5000/run';

exports.main_handler = async (event, context) => {
  try {
    // 1. 解析请求
    let requestBody;
    if (event.body) {
      requestBody = typeof event.body === 'string' 
        ? JSON.parse(event.body) 
        : event.body;
    } else {
      requestBody = event;
    }
    
    // 2. 提取用户消息
    const userMessage = requestBody.user_message;
    if (!userMessage) {
      return {
        statusCode: 400,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        },
        body: JSON.stringify({
          success: false,
          error: 'MISSING_PARAMETER',
          message: '缺少必填参数：user_message'
        })
      };
    }
    
    console.log('收到用户消息:', userMessage);
    
    // 3. 调用AI工作流API
    const response = await axios.post(
      AI_WORKFLOW_API_URL,
      { user_message: userMessage },
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: 30000
      }
    );
    
    // 4. 返回结果
    return {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      },
      body: JSON.stringify({
        success: true,
        reply_content: response.data.reply_content,
        run_id: response.data.run_id
      })
    };
    
  } catch (error) {
    console.error('错误:', error.message);
    
    const statusCode = error.code === 'ECONNABORTED' ? 504 : 500;
    
    return {
      statusCode,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      },
      body: JSON.stringify({
        success: false,
        error: statusCode === 504 ? 'TIMEOUT' : 'API_ERROR',
        message: error.message
      })
    };
  }
};
```

### 4.3 curl 测试示例

```bash
# 测试接口连通性
curl -X POST http://<服务器地址>:5000/run \
  -H "Content-Type: application/json" \
  -d '{"user_message": "你好"}'

# 测试使用指导场景
curl -X POST http://<服务器地址>:5000/run \
  -H "Content-Type: application/json" \
  -d '{"user_message": "我看到充电桩上有很多二维码，不知道应该扫哪一个？我是特斯拉的车。"}'

# 测试故障处理场景
curl -X POST http://<服务器地址>:5000/run \
  -H "Content-Type: application/json" \
  -d '{"user_message": "充电停不下来了，怎么办？"}'

# 测试投诉兜底场景
curl -X POST http://<服务器地址>:5000/run \
  -H "Content-Type: "application/json" \
  -d '{"user_message": "充电扣费异常，要求退款！手机号13800138000"}'
```

---

## 五、企业微信集成

### 5.1 集成架构

```
用户 → 企业微信 → 企业微信服务器 → 腾讯云函数 → AI工作流
                                                      ↓
用户 ← 企业微信 ← 企业微信服务器 ← 腾讯云函数 ← 回复内容
```

### 5.2 企业微信回调处理示例

```python
# -*- coding: utf-8 -*-
import json
import requests
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AI_WORKFLOW_API_URL = "http://<服务器地址>:5000/run"
WECHAT_API_TOKEN = "your_wechat_token"  # 企业微信Token


def parse_wechat_message(xml_data):
    """解析企业微信XML消息"""
    root = ET.fromstring(xml_data)
    return {
        'to_user': root.find('ToUserName').text,
        'from_user': root.find('FromUserName').text,
        'msg_type': root.find('MsgType').text,
        'content': root.find('Content').text if root.find('Content') is not None else '',
        'create_time': root.find('CreateTime').text
    }


def send_wechat_message(user_id, content):
    """发送消息到企业微信（通过应用）"""
    # 这里需要调用企业微信API发送消息
    # 参考：https://developer.work.weixin.qq.com/document/
    pass


def main_handler(event, context):
    """腾讯云函数入口 - 企业微信回调处理"""
    try:
        # 1. 解析企业微信回调
        if 'body' not in event:
            return {"statusCode": 400, "body": "Invalid request"}
        
        # 2. 解析XML消息
        message = parse_wechat_message(event['body'])
        user_content = message.get('content', '')
        from_user = message.get('from_user', '')
        
        if not user_content:
            return {"statusCode": 200, "body": "success"}
        
        logger.info(f"收到企业微信消息: {user_content}")
        
        # 3. 调用AI工作流
        response = requests.post(
            AI_WORKFLOW_API_URL,
            json={"user_message": user_content},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        # 4. 获取回复
        if response.status_code == 200:
            result = response.json()
            reply_content = result.get('reply_content', '')
            
            # 5. 发送回复到企业微信
            send_wechat_message(from_user, reply_content)
            
            logger.info(f"回复已发送: {reply_content[:50]}...")
        
        # 返回success告诉企业微信已处理
        return {"statusCode": 200, "body": "success"}
        
    except Exception as e:
        logger.error(f"处理失败: {e}", exc_info=True)
        return {"statusCode": 500, "body": "error"}


# 企业微信首次验证
def verify_wechat_signature(signature, timestamp, nonce, token):
    """验证企业微信签名"""
    import hashlib
    
    arr = [token, timestamp, nonce]
    arr.sort()
    tmp_str = ''.join(arr)
    tmp_str = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
    
    return tmp_str == signature
```

---

## 六、错误处理

### 6.1 错误码说明

| 错误码 | HTTP状态码 | 说明 | 处理建议 |
|--------|-----------|------|---------|
| `MISSING_PARAMETER` | 400 | 缺少必填参数 | 检查请求参数 |
| `INVALID_JSON` | 400 | JSON格式错误 | 检查JSON格式 |
| `API_ERROR` | 500 | AI工作流调用失败 | 重试或联系管理员 |
| `TIMEOUT` | 504 | API调用超时 | 增加超时时间或重试 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 | 查看日志并联系管理员 |

### 6.2 重试策略

建议在云函数中实现重试机制：

```python
import time

def call_ai_workflow_with_retry(user_message, max_retries=3):
    """带重试的API调用"""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                AI_WORKFLOW_API_URL,
                json={"user_message": user_message},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            elif response.status_code >= 500:
                # 服务器错误，重试
                time.sleep(1 * (attempt + 1))
                continue
            else:
                # 客户端错误，不重试
                return {"success": False, "error": response.text}
                
        except requests.Timeout:
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
                continue
            return {"success": False, "error": "Timeout after retries"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    return {"success": False, "error": "Max retries exceeded"}
```

---

## 七、性能与限制

### 7.1 性能指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 平均响应时间 | 3-5秒 | 知识库问答场景 |
| 最大响应时间 | 30秒 | 建议超时设置 |
| 并发支持 | 100+ | 可同时处理多个请求 |

### 7.2 限制说明

| 限制项 | 限制值 | 说明 |
|--------|--------|------|
| 单次请求消息长度 | 无限制 | 建议不超过1000字符 |
| 请求频率 | 无限制 | 建议<100次/分钟 |
| 超时时间 | 900秒 | 服务端最大超时 |

---

## 八、安全建议

### 8.1 当前状态

⚠️ **当前API无认证**，任何知道地址的人都可以调用。

### 8.2 推荐安全措施

#### 方案1：Token认证

在云函数中添加Token验证：

```python
# 在调用时添加Token
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_SECRET_TOKEN"
}
```

#### 方案2：IP白名单

在服务器防火墙配置中，只允许腾讯云函数的IP访问。

#### 方案3：企业微信签名验证

验证请求确实来自企业微信服务器。

---

## 九、监控与日志

### 9.1 日志查看

**AI工作流日志**：
```
服务器日志路径：/app/work/logs/bypass/app.log
```

**腾讯云函数日志**：
```
腾讯云控制台 → 云函数 → 日志查询
```

### 9.2 监控指标

建议监控以下指标：

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| 调用成功率 | 成功调用/总调用 | <95% |
| 平均响应时间 | API响应耗时 | >5秒 |
| 错误率 | 错误响应/总响应 | >5% |

---

## 十、常见问题

### Q1: 如何获取API访问地址？

**A**: API地址格式为 `http://<服务器公网IP>:5000/run`，需要：
1. 部署AI工作流到服务器
2. 确保服务器有公网IP
3. 开放5000端口（安全组配置）

### Q2: API调用超时怎么办？

**A**: 
1. 增加云函数超时时间（最大900秒）
2. 检查服务器负载
3. 联系管理员排查问题

### Q3: 如何测试API是否正常？

**A**: 使用curl或Postman测试：
```bash
curl -X POST http://<服务器地址>:5000/health
```

### Q4: 响应内容乱码怎么办？

**A**: 确保请求头包含：
```
Content-Type: application/json; charset=utf-8
```

### Q5: 如何获取历史对话？

**A**: 当前版本不支持多轮对话历史，每次请求都是独立的。

---

## 十一、联系方式

### 技术支持

- **问题反馈**：请联系项目负责人
- **紧急问题**：请查看服务器日志排查

### 文档版本

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2026-03 | 初始版本 |

---

## 附录A：完整测试用例

### A.1 使用指导场景

**请求**：
```json
{
  "user_message": "我看到充电桩上有很多二维码，不知道应该扫哪一个？我是特斯拉的车。"
}
```

**预期响应**：
```json
{
  "reply_content": "您好！如果您是特斯拉车辆，请查看充电桩正面显示屏下方...",
  "run_id": "xxx-xxx-xxx"
}
```

### A.2 故障处理场景

**请求**：
```json
{
  "user_message": "充电停不下来了，我点了停止按钮但是还在继续充电，怎么办？"
}
```

**预期响应**：
```json
{
  "reply_content": "很抱歉给您带来困扰。如果充电停不下来，请尝试以下方法...",
  "run_id": "xxx-xxx-xxx"
}
```

### A.3 投诉兜底场景

**请求**：
```json
{
  "user_message": "充电扣费异常，要求退款！手机号13800138000，订单号12345678"
}
```

**预期响应**：
```json
{
  "reply_content": "感谢您的反馈！我们已收到您的问题，客服人员会在1个工作日内联系您...",
  "run_id": "xxx-xxx-xxx"
}
```

---

**文档结束**
