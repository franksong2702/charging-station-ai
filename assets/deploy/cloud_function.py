# 腾讯云函数 - 充电桩智能客服（企业微信版）
# 版本: v1.0
# 说明: 接收企业微信消息，调用AI工作流，返回回复

import json
import requests
import logging
import hashlib
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ==================== 配置区（请修改为您的实际配置）====================
# AI工作流API地址（替换为您的服务器地址）
AI_WORKFLOW_API_URL = "http://YOUR_SERVER_IP:5000/run"

# 企业微信配置（从企业微信后台获取）
WECHAT_CORP_ID = ""           # 企业ID
WECHAT_AGENT_ID = ""          # 应用AgentId
WECHAT_SECRET = ""            # 应用Secret
WECHAT_TOKEN = ""             # 应用Token（用于验证消息）
WECHAT_ENCODING_AES_KEY = ""  # 应用的EncodingAESKey（加密用，可选）

# 是否启用消息加密（推荐生产环境启用）
ENABLE_ENCRYPTION = False
# ==================== 配置区结束 ====================


# ==================== 工具函数 ====================

def verify_signature(signature: str, timestamp: str, nonce: str, token: str) -> bool:
    """
    验证企业微信消息签名
    
    Args:
        signature: 企业微信发送的签名
        timestamp: 时间戳
        nonce: 随机数
        token: 您设置的Token
    
    Returns:
        签名是否有效
    """
    if not token:
        return True  # 如果没有配置Token，跳过验证
    
    try:
        arr = [token, timestamp, nonce]
        arr.sort()
        tmp_str = ''.join(arr)
        tmp_str = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
        return tmp_str == signature
    except Exception as e:
        logger.error(f"签名验证失败: {e}")
        return False


def parse_xml_message(xml_data: str) -> Dict[str, Any]:
    """
    解析企业微信XML消息
    
    Args:
        xml_data: XML格式的消息数据
    
    Returns:
        解析后的消息字典
    """
    try:
        root = ET.fromstring(xml_data)
        message = {}
        
        for child in root:
            message[child.tag] = child.text
        
        return message
    except Exception as e:
        logger.error(f"XML解析失败: {e}")
        return {}


def call_ai_workflow(user_message: str) -> Dict[str, Any]:
    """
    调用AI工作流API
    
    Args:
        user_message: 用户消息
    
    Returns:
        API响应结果
    """
    try:
        response = requests.post(
            AI_WORKFLOW_API_URL,
            json={"user_message": user_message},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "reply_content": result.get("reply_content", ""),
                "run_id": result.get("run_id", "")
            }
        else:
            logger.error(f"AI工作流调用失败: {response.status_code} - {response.text}")
            return {
                "success": False,
                "error": f"API调用失败: {response.status_code}"
            }
    
    except requests.Timeout:
        logger.error("AI工作流调用超时")
        return {"success": False, "error": "请求超时"}
    
    except Exception as e:
        logger.error(f"AI工作流调用异常: {e}")
        return {"success": False, "error": str(e)}


def get_wechat_access_token() -> Optional[str]:
    """
    获取企业微信access_token
    
    Returns:
        access_token或None
    """
    if not WECHAT_CORP_ID or not WECHAT_SECRET:
        logger.warning("未配置企业微信CorpId或Secret")
        return None
    
    try:
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {
            "corpid": WECHAT_CORP_ID,
            "corpsecret": WECHAT_SECRET
        }
        
        response = requests.get(url, params=params, timeout=10)
        result = response.json()
        
        if result.get("errcode") == 0:
            return result.get("access_token")
        else:
            logger.error(f"获取access_token失败: {result}")
            return None
    
    except Exception as e:
        logger.error(f"获取access_token异常: {e}")
        return None


def send_wechat_message(user_id: str, content: str) -> bool:
    """
    发送消息到企业微信用户
    
    Args:
        user_id: 用户ID
        content: 消息内容
    
    Returns:
        是否发送成功
    """
    access_token = get_wechat_access_token()
    if not access_token:
        logger.error("无法获取access_token")
        return False
    
    try:
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        
        payload = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": WECHAT_AGENT_ID,
            "text": {
                "content": content
            },
            "safe": 0
        }
        
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if result.get("errcode") == 0:
            logger.info(f"消息发送成功: {user_id}")
            return True
        else:
            logger.error(f"消息发送失败: {result}")
            return False
    
    except Exception as e:
        logger.error(f"消息发送异常: {e}")
        return False


# ==================== 主处理函数 ====================

def main_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    腾讯云函数入口
    
    Args:
        event: 触发器事件数据
        context: 运行上下文
    
    Returns:
        API网关响应格式
    """
    try:
        # ==================== 处理企业微信首次验证 ====================
        # 企业微信配置回调URL时会发送GET请求验证
        query_params = event.get('queryString', {}) or event.get('query', {})
        
        if query_params.get('msg_signature') or query_params.get('signature'):
            # 验证签名
            signature = query_params.get('msg_signature') or query_params.get('signature', '')
            timestamp = query_params.get('timestamp', '')
            nonce = query_params.get('nonce', '')
            echostr = query_params.get('echostr', '')
            
            # 验证签名
            if verify_signature(signature, timestamp, nonce, WECHAT_TOKEN):
                logger.info("企业微信验证成功")
                # 首次验证需要返回echostr
                if echostr:
                    return {
                        "statusCode": 200,
                        "body": echostr
                    }
            else:
                logger.warning("企业微信验证失败")
                return {
                    "statusCode": 403,
                    "body": "验证失败"
                }
        
        # ==================== 处理企业微信消息 ====================
        if 'body' in event:
            body = event.get('body', '')
            
            # 如果是字符串，尝试解析
            if isinstance(body, str):
                # 尝试解析JSON
                try:
                    request_data = json.loads(body)
                except json.JSONDecodeError:
                    # 可能是XML格式
                    request_data = parse_xml_message(body)
            else:
                request_data = body
            
            logger.info(f"收到请求: {json.dumps(request_data, ensure_ascii=False)[:200]}")
            
            # 提取用户消息
            user_message = (
                request_data.get('Content') or 
                request_data.get('content') or
                request_data.get('user_message') or
                request_data.get('message')
            )
            
            # 提取发送者信息
            from_user = request_data.get('FromUserName', '')
            
            if not user_message:
                # 可能是企业微信验证请求
                return {
                    "statusCode": 200,
                    "body": "success"
                }
            
            logger.info(f"用户消息: {user_message}")
            
            # ==================== 调用AI工作流 ====================
            result = call_ai_workflow(user_message)
            
            if not result['success']:
                # 调用失败，返回错误消息
                error_reply = "抱歉，系统暂时无法处理您的请求，请稍后重试。"
                send_wechat_message(from_user, error_reply)
                
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "success": False,
                        "error": result.get('error', '未知错误')
                    }, ensure_ascii=False)
                }
            
            # ==================== 发送回复到企业微信 ====================
            reply_content = result['reply_content']
            send_success = send_wechat_message(from_user, reply_content)
            
            # ==================== 返回响应 ====================
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": True,
                    "reply_content": reply_content,
                    "run_id": result.get('run_id', ''),
                    "wechat_sent": send_success
                }, ensure_ascii=False)
            }
        
        # ==================== 处理直接调用（测试用）====================
        else:
            user_message = event.get('user_message') or event.get('message')
            
            if not user_message:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "success": False,
                        "error": "缺少参数：user_message"
                    }, ensure_ascii=False)
                }
            
            logger.info(f"直接调用 - 用户消息: {user_message}")
            
            # 调用AI工作流
            result = call_ai_workflow(user_message)
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": result['success'],
                    "reply_content": result.get('reply_content', ''),
                    "run_id": result.get('run_id', ''),
                    "error": result.get('error', '')
                }, ensure_ascii=False)
            }
    
    except Exception as e:
        logger.error(f"处理异常: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "error": f"服务器错误: {str(e)}"
            }, ensure_ascii=False)
        }


# ==================== 本地测试 ====================
if __name__ == '__main__':
    # 测试1: 直接调用
    test_event = {
        "user_message": "充电停不下来了怎么办？"
    }
    result = main_handler(test_event, None)
    print("测试1 - 直接调用:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 测试2: 模拟企业微信回调
    test_event_wechat = {
        "body": "<xml><ToUserName>corp_id</ToUserName><FromUserName>user123</FromUserName><CreateTime>1234567890</CreateTime><MsgType>text</MsgType><Content>充电枪拔不出来了</Content><MsgId>123456</MsgId><AgentId>100001</AgentId></xml>"
    }
    result = main_handler(test_event_wechat, None)
    print("\n测试2 - 企业微信回调:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
