"""
充电桩智能客服工作流测试用例
版本: v1.1.0

测试场景覆盖：
1. 意图识别测试
2. 知识库问答测试（优化后的搜索策略）
3. 兜底流程测试
4. 评价反馈测试
5. 多轮对话状态管理测试
"""

import pytest
from typing import Dict, Any, List

# 测试用例数据结构
TestCase = Dict[str, Any]


# ==================== 意图识别测试用例 ====================

INTENT_RECOGNITION_TEST_CASES: List[TestCase] = [
    # 使用指导类
    {
        "id": "IR001",
        "name": "使用指导-特斯拉充电",
        "input": {"user_message": "特斯拉的车怎么充电"},
        "expected_intent": "usage_guidance",
        "description": "用户询问特斯拉充电方式，应识别为使用指导"
    },
    {
        "id": "IR002",
        "name": "使用指导-比亚迪充电",
        "input": {"user_message": "比亚迪怎么充电"},
        "expected_intent": "usage_guidance",
        "description": "用户询问比亚迪充电方式，应识别为使用指导"
    },
    {
        "id": "IR003",
        "name": "使用指导-扫码位置",
        "input": {"user_message": "二维码在哪扫"},
        "expected_intent": "usage_guidance",
        "description": "用户询问扫码位置，应识别为使用指导"
    },
    {
        "id": "IR004",
        "name": "使用指导-第一次使用",
        "input": {"user_message": "第一次用充电桩，怎么操作"},
        "expected_intent": "usage_guidance",
        "description": "新手询问使用方法，应识别为使用指导"
    },
    
    # 故障处理类
    {
        "id": "IR005",
        "name": "故障处理-充不进去",
        "input": {"user_message": "充不进去电怎么办"},
        "expected_intent": "fault_handling",
        "description": "充电失败问题，应识别为故障处理"
    },
    {
        "id": "IR006",
        "name": "故障处理-充不上",
        "input": {"user_message": "充不上电"},
        "expected_intent": "fault_handling",
        "description": "充电失败问题，应识别为故障处理"
    },
    {
        "id": "IR007",
        "name": "故障处理-充电失败",
        "input": {"user_message": "充电失败怎么回事"},
        "expected_intent": "fault_handling",
        "description": "充电失败问题，应识别为故障处理"
    },
    {
        "id": "IR008",
        "name": "故障处理-充电枪拔不出来",
        "input": {"user_message": "充电枪拔不出来怎么办"},
        "expected_intent": "fault_handling",
        "description": "充电枪卡住问题，应识别为故障处理"
    },
    {
        "id": "IR009",
        "name": "故障处理-充电停不下来",
        "input": {"user_message": "充电停不下来"},
        "expected_intent": "fault_handling",
        "description": "充电停止问题，应识别为故障处理"
    },
    {
        "id": "IR010",
        "name": "故障处理-设备故障",
        "input": {"user_message": "充电桩坏了"},
        "expected_intent": "fault_handling",
        "description": "设备故障问题，应识别为故障处理"
    },
    
    # 轻度不满类
    {
        "id": "IR011",
        "name": "轻度不满-没用",
        "input": {"user_message": "你这回答没用啊"},
        "expected_intent": "dissatisfied",
        "description": "轻度不满表达，应识别为不满意"
    },
    {
        "id": "IR012",
        "name": "轻度不满-没帮助",
        "input": {"user_message": "没什么帮助"},
        "expected_intent": "dissatisfied",
        "description": "轻度不满表达，应识别为不满意"
    },
    {
        "id": "IR013",
        "name": "轻度不满-还是不行",
        "input": {"user_message": "还是不行"},
        "expected_intent": "dissatisfied",
        "description": "轻度不满表达，应识别为不满意"
    },
    {
        "id": "IR014",
        "name": "轻度不满-我很不满意",
        "input": {"user_message": "我很不满意"},
        "expected_intent": "dissatisfied",
        "description": "轻度不满表达，应识别为不满意"
    },
    
    # 强烈不满/兜底类
    {
        "id": "IR015",
        "name": "强烈不满-垃圾",
        "input": {"user_message": "什么垃圾服务"},
        "expected_intent": "fallback",
        "description": "强烈不满表达，应触发兜底流程"
    },
    {
        "id": "IR016",
        "name": "强烈不满-投诉",
        "input": {"user_message": "我要投诉你"},
        "expected_intent": "fallback",
        "description": "投诉表达，应触发兜底流程"
    },
    {
        "id": "IR017",
        "name": "强烈不满-转人工",
        "input": {"user_message": "转人工客服"},
        "expected_intent": "fallback",
        "description": "要求转人工，应触发兜底流程"
    },
    {
        "id": "IR018",
        "name": "强烈不满-太差了",
        "input": {"user_message": "服务太差了"},
        "expected_intent": "fallback",
        "description": "强烈不满表达，应触发兜底流程"
    },
    
    # 满意类
    {
        "id": "IR019",
        "name": "满意-谢谢",
        "input": {"user_message": "谢谢"},
        "expected_intent": "satisfied",
        "description": "感谢表达，应识别为满意"
    },
    {
        "id": "IR020",
        "name": "满意-感谢",
        "input": {"user_message": "非常感谢"},
        "expected_intent": "satisfied",
        "description": "感谢表达，应识别为满意"
    },
    
    # 评价反馈类
    {
        "id": "IR021",
        "name": "评价反馈-好评数字",
        "input": {"user_message": "1"},
        "expected_intent": "feedback_good",
        "description": "数字1表示好评"
    },
    {
        "id": "IR022",
        "name": "评价反馈-差评数字",
        "input": {"user_message": "2"},
        "expected_intent": "feedback_bad",
        "description": "数字2表示差评"
    },
    {
        "id": "IR023",
        "name": "评价反馈-好评文字",
        "input": {"user_message": "很好"},
        "expected_intent": "feedback_good",
        "description": "文字好评"
    },
    {
        "id": "IR024",
        "name": "评价反馈-差评文字",
        "input": {"user_message": "没有帮助"},
        "expected_intent": "feedback_bad",
        "description": "文字差评"
    },
]


# ==================== 知识库问答测试用例 ====================

KNOWLEDGE_QA_TEST_CASES: List[TestCase] = [
    # 品牌充电指引（v1.1.0 优化重点）
    {
        "id": "KQ001",
        "name": "特斯拉充电指引",
        "input": {"user_message": "特斯拉的车怎么充电"},
        "expected_keywords": ["充电桩正面", "黑白二维码", "显示屏下方"],
        "expected_not_contains": ["暂无相关指引"],
        "description": "特斯拉充电应返回正面显示屏下方的黑白二维码"
    },
    {
        "id": "KQ002",
        "name": "比亚迪充电指引",
        "input": {"user_message": "比亚迪的车怎么充电"},
        "expected_keywords": ["充电桩侧面", "彩色二维码", "顶部"],
        "expected_not_contains": ["暂无相关指引"],
        "description": "比亚迪充电应返回侧面或顶部的彩色二维码"
    },
    {
        "id": "KQ003",
        "name": "特斯拉扫码位置",
        "input": {"user_message": "特斯拉在哪个位置扫码"},
        "expected_keywords": ["充电桩正面", "黑白二维码"],
        "expected_not_contains": ["暂无相关指引"],
        "description": "特斯拉扫码位置查询"
    },
    {
        "id": "KQ004",
        "name": "比亚迪扫码位置",
        "input": {"user_message": "比亚迪二维码在哪"},
        "expected_keywords": ["充电桩侧面", "彩色二维码"],
        "expected_not_contains": ["暂无相关指引"],
        "description": "比亚迪扫码位置查询"
    },
    
    # 故障处理类
    {
        "id": "KQ005",
        "name": "无法充电故障",
        "input": {"user_message": "充不进去电怎么办"},
        "expected_keywords": ["检查", "充电枪", "插好"],
        "expected_not_contains": ["暂无相关指引"],
        "description": "无法充电故障处理"
    },
    {
        "id": "KQ006",
        "name": "充电枪拔不出来",
        "input": {"user_message": "充电枪拔不出来怎么办"},
        "expected_keywords": ["解锁", "车辆", "联系客服"],
        "expected_not_contains": ["暂无相关指引"],
        "description": "充电枪卡住处理"
    },
    {
        "id": "KQ007",
        "name": "充电失败处理",
        "input": {"user_message": "扫码后无法启动充电"},
        "expected_keywords": ["充电枪", "插好", "支付"],
        "expected_not_contains": ["暂无相关指引"],
        "description": "充电启动失败处理"
    },
    
    # 使用流程类
    {
        "id": "KQ008",
        "name": "第一次使用流程",
        "input": {"user_message": "第一次用充电桩，完整流程是什么"},
        "expected_keywords": ["扫码", "插枪", "充电"],
        "expected_not_contains": ["暂无相关指引"],
        "description": "新手完整使用流程"
    },
    {
        "id": "KQ009",
        "name": "充电费用计算",
        "input": {"user_message": "充电费用怎么算"},
        "expected_keywords": ["电费", "服务费"],
        "expected_not_contains": ["暂无相关指引"],
        "description": "计费规则查询"
    },
    {
        "id": "KQ010",
        "name": "附近充电站",
        "input": {"user_message": "怎么找附近的充电桩"},
        "expected_keywords": ["小程序", "附近", "地图"],
        "expected_not_contains": ["暂无相关指引"],
        "description": "查找充电站"
    },
    
    # 边界测试
    {
        "id": "KQ011",
        "name": "问候语处理",
        "input": {"user_message": "你好"},
        "expected_keywords": [],  # 无特定关键词要求
        "expected_not_contains": [],
        "description": "简单问候，检查是否有合理回复"
    },
    {
        "id": "KQ012",
        "name": "模糊问题处理",
        "input": {"user_message": "充电"},
        "expected_keywords": [],
        "expected_not_contains": [],
        "description": "模糊问题，检查是否有合理回复"
    },
]


# ==================== 兜底流程测试用例 ====================

FALLBACK_FLOW_TEST_CASES: List[TestCase] = [
    # 兜底流程触发
    {
        "id": "FB001",
        "name": "触发兜底流程-投诉",
        "input": {"user_message": "我要投诉你们"},
        "expected_phase": "collect_info",
        "expected_keywords": ["手机号", "车牌号"],
        "description": "投诉触发兜底流程，开始收集信息"
    },
    {
        "id": "FB002",
        "name": "触发兜底流程-转人工",
        "input": {"user_message": "转人工客服"},
        "expected_phase": "collect_info",
        "expected_keywords": ["手机号", "车牌号"],
        "description": "转人工触发兜底流程"
    },
    {
        "id": "FB003",
        "name": "触发兜底流程-强烈不满",
        "input": {"user_message": "什么垃圾服务，气死我了"},
        "expected_phase": "collect_info",
        "expected_keywords": ["手机号", "车牌号"],
        "description": "强烈不满触发兜底流程"
    },
    
    # 兜底流程中输入信息
    {
        "id": "FB004",
        "name": "兜底流程-输入手机号",
        "input": {
            "user_message": "13800138000",
            "fallback_phase": "collect_info"
        },
        "expected_phase": "collect_info",
        "expected_keywords": ["车牌号"],
        "description": "输入手机号后，继续收集车牌号"
    },
    {
        "id": "FB005",
        "name": "兜底流程-输入车牌号",
        "input": {
            "user_message": "京A12345",
            "fallback_phase": "collect_info",
            "collected_phone": "13800138000"
        },
        "expected_phase": "confirm",
        "expected_keywords": ["确认", "问题总结"],
        "description": "信息收集完成，生成问题总结等待确认"
    },
    {
        "id": "FB006",
        "name": "兜底流程-用户确认",
        "input": {
            "user_message": "确认",
            "fallback_phase": "confirm",
            "collected_phone": "13800138000",
            "collected_plate": "京A12345",
            "problem_summary": "充电桩故障无法使用"
        },
        "expected_phase": "done",
        "expected_keywords": ["工单", "已提交"],
        "description": "用户确认后创建工单"
    },
    
    # 退出兜底流程
    {
        "id": "FB007",
        "name": "退出兜底流程-取消",
        "input": {
            "user_message": "取消",
            "fallback_phase": "collect_info"
        },
        "expected_phase": "",
        "expected_keywords": [],
        "description": "用户取消兜底流程"
    },
    {
        "id": "FB008",
        "name": "退出兜底流程-问新问题",
        "input": {
            "user_message": "特斯拉怎么充电",
            "fallback_phase": "collect_info"
        },
        "expected_phase": "",
        "expected_keywords": ["充电桩正面", "黑白二维码"],
        "description": "用户问新问题，退出兜底流程"
    },
    
    # 兜底流程完成后
    {
        "id": "FB009",
        "name": "兜底完成后-新会话",
        "input": {
            "user_message": "你好",
            "fallback_phase": "done"
        },
        "expected_phase": "",
        "expected_keywords": [],
        "description": "兜底完成后，下次对话为新会话"
    },
]


# ==================== 评价反馈测试用例 ====================

FEEDBACK_TEST_CASES: List[TestCase] = [
    {
        "id": "FB_EVAL001",
        "name": "好评-数字1",
        "input": {"user_message": "1"},
        "expected_feedback": "good",
        "expected_keywords": ["感谢", "评价"],
        "description": "数字1表示好评"
    },
    {
        "id": "FB_EVAL002",
        "name": "好评-全角数字",
        "input": {"user_message": "１"},
        "expected_feedback": "good",
        "expected_keywords": ["感谢", "评价"],
        "description": "全角数字1表示好评"
    },
    {
        "id": "FB_EVAL003",
        "name": "好评-文字",
        "input": {"user_message": "很好"},
        "expected_feedback": "good",
        "expected_keywords": ["感谢"],
        "description": "文字好评"
    },
    {
        "id": "FB_EVAL004",
        "name": "差评-数字2",
        "input": {"user_message": "2"},
        "expected_feedback": "bad",
        "expected_keywords": ["抱歉", "反馈"],
        "description": "数字2表示差评"
    },
    {
        "id": "FB_EVAL005",
        "name": "差评-全角数字",
        "input": {"user_message": "２"},
        "expected_feedback": "bad",
        "expected_keywords": ["抱歉", "反馈"],
        "description": "全角数字2表示差评"
    },
    {
        "id": "FB_EVAL006",
        "name": "差评-文字",
        "input": {"user_message": "没有帮助"},
        "expected_feedback": "bad",
        "expected_keywords": ["抱歉"],
        "description": "文字差评"
    },
]


# ==================== 多轮对话测试用例 ====================

MULTI_TURN_TEST_CASES: List[TestCase] = [
    {
        "id": "MT001",
        "name": "多轮对话-正常问答",
        "turns": [
            {"user_message": "特斯拉怎么充电", "expected_intent": "usage_guidance"},
            {"user_message": "谢谢", "expected_intent": "satisfied"},
        ],
        "description": "正常问答后感谢"
    },
    {
        "id": "MT002",
        "name": "多轮对话-不满后继续",
        "turns": [
            {"user_message": "你好", "expected_intent": "usage_guidance"},
            {"user_message": "没用", "expected_intent": "dissatisfied"},
            {"user_message": "特斯拉怎么充电", "expected_intent": "usage_guidance"},
        ],
        "description": "不满后继续提问"
    },
    {
        "id": "MT003",
        "name": "多轮对话-兜底流程完整",
        "turns": [
            {"user_message": "我要投诉", "expected_intent": "fallback", "expected_phase": "collect_info"},
            {"user_message": "13800138000", "expected_intent": "fallback", "expected_phase": "collect_info"},
            {"user_message": "京A12345", "expected_intent": "fallback", "expected_phase": "confirm"},
            {"user_message": "确认", "expected_intent": "fallback", "expected_phase": "done"},
        ],
        "description": "完整兜底流程"
    },
    {
        "id": "MT004",
        "name": "多轮对话-兜底中途退出",
        "turns": [
            {"user_message": "转人工", "expected_intent": "fallback", "expected_phase": "collect_info"},
            {"user_message": "算了取消", "expected_intent": "cancel_fallback", "expected_phase": ""},
        ],
        "description": "兜底流程中途取消"
    },
]


# ==================== 边界和异常测试用例 ====================

EDGE_CASE_TEST_CASES: List[TestCase] = [
    {
        "id": "EC001",
        "name": "空消息处理",
        "input": {"user_message": ""},
        "description": "空消息应正常处理"
    },
    {
        "id": "EC002",
        "name": "超长消息处理",
        "input": {"user_message": "这是一个很长的消息" * 100},
        "description": "超长消息应正常处理"
    },
    {
        "id": "EC003",
        "name": "特殊字符处理",
        "input": {"user_message": "充电@#$%^&*()_+{}|:\"<>?"},
        "description": "特殊字符应正常处理"
    },
    {
        "id": "EC004",
        "name": "英文消息处理",
        "input": {"user_message": "How to charge Tesla?"},
        "description": "英文消息应正常处理"
    },
    {
        "id": "EC005",
        "name": "混合语言处理",
        "input": {"user_message": "Tesla 特斯拉怎么充电"},
        "description": "混合语言应正常处理"
    },
    {
        "id": "EC006",
        "name": "手机号多种格式",
        "input": {
            "user_message": "138-0013-8000",
            "fallback_phase": "collect_info"
        },
        "description": "带分隔符的手机号应能识别"
    },
    {
        "id": "EC007",
        "name": "车牌号多种格式",
        "input": {
            "user_message": "京A一二三四五",
            "fallback_phase": "collect_info"
        },
        "description": "中文数字车牌号应能识别"
    },
]


def get_all_test_cases() -> Dict[str, List[TestCase]]:
    """
    获取所有测试用例
    
    Returns:
        按类别分组的测试用例字典
    """
    return {
        "intent_recognition": INTENT_RECOGNITION_TEST_CASES,
        "knowledge_qa": KNOWLEDGE_QA_TEST_CASES,
        "fallback_flow": FALLBACK_FLOW_TEST_CASES,
        "feedback": FEEDBACK_TEST_CASES,
        "multi_turn": MULTI_TURN_TEST_CASES,
        "edge_case": EDGE_CASE_TEST_CASES,
    }


def get_test_case_by_id(test_id: str) -> TestCase:
    """
    根据ID获取测试用例
    
    Args:
        test_id: 测试用例ID
        
    Returns:
        测试用例或None
    """
    for category, cases in get_all_test_cases().items():
        for case in cases:
            if case.get("id") == test_id:
                return {**case, "category": category}
    return None


def print_test_summary():
    """打印测试用例摘要"""
    all_cases = get_all_test_cases()
    print("=" * 60)
    print("充电桩智能客服工作流测试用例摘要 (v1.1.0)")
    print("=" * 60)
    
    total = 0
    for category, cases in all_cases.items():
        count = len(cases)
        total += count
        print(f"\n{category}: {count} 个测试用例")
        for case in cases:
            print(f"  - [{case['id']}] {case['name']}")
    
    print(f"\n总计: {total} 个测试用例")
    print("=" * 60)


if __name__ == "__main__":
    print_test_summary()
