# -*- coding: utf-8 -*-
"""
腾讯云函数 - 充电桩智能客服API调用示例

使用方法：
1. 在腾讯云函数控制台创建Python函数
2. 将此代码复制到函数中
3. 配置环境变量 COZE_API_URL
4. 配置API网关触发器
"""

import json
import requests
import logging
from typing import Dict, Any

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def main_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    腾讯云函数入口函数
    
    Args:
        event: 触发器事件数据（API网关触发器会传入HTTP请求数据）
        context: 运行上下文
    
    Returns:
        API网关响应格式
    """
    logger.info(f"Received event: {json.dumps(event, ensure_ascii=False)}")
    
    # ==================== 配置区 ====================
    # 方式1：从环境变量读取（推荐）
    # 在腾讯云函数配置中添加环境变量：COZE_API_URL = https://your-domain.com/run
    COZE_API_URL = "https://your-domain.com/run"  # 替换为您的Coze API地址
    
    # 方式2：直接写死（测试用）
    # COZE_API_URL = "https://your-domain.com/run"
    # ==================== 配置区结束 ====================
    
    try:
        # 1. 解析请求
        # API网关触发器会传入完整的HTTP请求
        if 'body' in event:
            # 来自API网关的请求
            body = event.get('body', '{}')
            if isinstance(body, str):
                request_data = json.loads(body)
            else:
                request_data = body
        else:
            # 直接调用
            request_data = event
        
        # 2. 提取用户消息
        user_message = request_data.get('user_message') or request_data.get('message') or request_data.get('content')
        
        if not user_message:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": False,
                    "error": "缺少必填参数：user_message",
                    "message": "请提供用户消息内容"
                }, ensure_ascii=False)
            }
        
        logger.info(f"User message: {user_message}")
        
        # 3. 调用Coze API
        coze_payload = {
            "user_message": user_message
        }
        
        coze_response = requests.post(
            COZE_API_URL,
            json=coze_payload,
            headers={"Content-Type": "application/json"},
            timeout=30  # 30秒超时
        )
        
        # 4. 处理响应
        if coze_response.status_code != 200:
            logger.error(f"Coze API error: {coze_response.status_code} - {coze_response.text}")
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": False,
                    "error": "Coze API调用失败",
                    "detail": coze_response.text
                }, ensure_ascii=False)
            }
        
        result = coze_response.json()
        reply_content = result.get('reply_content', '')
        run_id = result.get('run_id', '')
        
        logger.info(f"Reply content: {reply_content}")
        
        # 5. 返回成功响应
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps({
                "success": True,
                "reply_content": reply_content,
                "run_id": run_id,
                "message": "处理成功"
            }, ensure_ascii=False)
        }
        
    except requests.Timeout:
        logger.error("Coze API timeout")
        return {
            "statusCode": 504,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "success": False,
                "error": "请求超时",
                "message": "Coze API响应超时，请稍后重试"
            }, ensure_ascii=False)
        }
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "success": False,
                "error": "JSON格式错误",
                "message": str(e)
            }, ensure_ascii=False)
        }
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "success": False,
                "error": "服务器内部错误",
                "message": str(e)
            }, ensure_ascii=False)
        }


# ==================== 本地测试代码 ====================
if __name__ == '__main__':
    # 模拟API网关事件
    test_event = {
        "body": json.dumps({
            "user_message": "我看到充电桩上有很多二维码，不知道应该扫哪一个？我是特斯拉的车。"
        })
    }
    
    result = main_handler(test_event, None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
