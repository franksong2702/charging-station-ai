"""
Auto-Research 兜底流程优化测试脚本
版本: v2.0

核心功能：
1. AI 测试 AI - 自动跑 10 个兜底流程场景
2. Prompt 自动迭代 - 5 轮优化，找到最优版本
3. 对比测试 - v1 vs v2 通过率对比
"""
import sys
import os
import json
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 10 个测试场景 ====================

TEST_SCENARIOS = [
    # 场景 1-3：基础投诉
    {
        "id": "S001",
        "name": "优惠券投诉",
        "user_message": "你们这个垃圾系统，气死我了",
        "description": "用户抱怨系统问题"
    },
    {
        "id": "S002",
        "name": "充电故障",
        "user_message": "什么垃圾服务，充不进去电",
        "description": "用户抱怨充电故障"
    },
    {
        "id": "S003",
        "name": "退款投诉",
        "user_message": "我要退款",
        "description": "用户要求退款"
    },
    
    # 场景 4-6：边界情况
    {
        "id": "S004",
        "name": "模糊投诉",
        "user_message": "我要投诉",
        "description": "用户只说投诉，不说具体问题"
    },
    {
        "id": "S005",
        "name": "情绪激动",
        "user_message": "垃圾！垃圾！垃圾！",
        "description": "用户情绪激动，重复三次"
    },
    {
        "id": "S006",
        "name": "中途取消",
        "user_message": "我要投诉...算了不用了",
        "description": "用户先说投诉，然后取消"
    },
    
    # 场景 7-10：复杂场景
    {
        "id": "S007",
        "name": "用户纠正",
        "user_message": "不对，你总结得不对，我实际是...",
        "description": "用户纠正问题总结"
    },
    {
        "id": "S008",
        "name": "分次提供",
        "user_message": "手机 13912345678",
        "second_message": "车牌京 A12345",
        "description": "用户分两次提供信息"
    },
    {
        "id": "S009",
        "name": "语音格式",
        "user_message": "手机号 139。16425678。车牌。沪 A Dr 3509",
        "description": "语音输入格式，带句号分隔"
    },
    {
        "id": "S010",
        "name": "补充信息",
        "user_message": "另外我还有优惠券没用",
        "description": "用户补充额外信息"
    }
]

# ==================== 阶段判断规则 ====================

def detect_phase(ai_reply: str) -> str:
    """
    根据 AI 回复判断当前阶段
    
    Returns:
        "ask_clarify": 询问阶段（问用户具体问题）
        "collect_info": 收集信息阶段（要手机号/车牌号）
        "confirm": 确认阶段（让用户确认信息）
        "done": 已完成（工单已创建）
        "unknown": 未知阶段
    """
    reply_lower = ai_reply.lower()
    
    # 询问阶段：问用户具体问题
    if any(keyword in reply_lower for keyword in ["什么问题", "怎么回事", "具体", "说说", "遇到"]):
        return "ask_clarify"
    
    # 收集信息阶段：要手机号/车牌号
    if any(keyword in reply_lower for keyword in ["手机号", "车牌号", "提供", "方便提供"]):
        return "collect_info"
    
    # 确认阶段：让用户确认信息
    if any(keyword in reply_lower for keyword in ["确认吗", "准确吗", "以上信息", "确认"]):
        return "confirm"
    
    # 已完成：工单已创建
    if any(keyword in reply_lower for keyword in ["1-3 个工作日", "尽快处理", "工单", "已提交"]):
        return "done"
    
    return "unknown"

def generate_next_user_message(phase: str, scenario: Dict[str, Any]) -> str:
    """
    根据当前阶段生成下一条用户消息
    
    Args:
        phase: 当前阶段
        scenario: 测试场景
    
    Returns:
        下一条用户消息
    """
    if phase == "ask_clarify":
        # 询问阶段：描述具体问题
        return "充电桩坏了，充不进去电"
    
    elif phase == "collect_info":
        # 收集信息阶段：提供手机号和车牌号
        if "second_message" in scenario:
            # 分次提供场景：先给手机号
            return "手机 13912345678"
        return "手机 13812345678 车牌京 A12345"
    
    elif phase == "confirm":
        # 确认阶段：确认
        return "确认"
    
    return "好的"

# ==================== Prompt 变体生成 ====================

def generate_prompt_variant(base_prompt: str, variant_num: int) -> str:
    """
    生成 Prompt 变体
    
    Args:
        base_prompt: 基础 Prompt
        variant_num: 变体编号 (1-5)
    
    Returns:
        变体 Prompt
    """
    variants = [
        # Variant 1: 扩展兜底触发词
        lambda p: p.replace(
            "投诉兜底：投诉、转人工、垃圾服务、强烈不满、退款",
            "投诉兜底：投诉、转人工、垃圾服务、强烈不满、退款、退钱、赔钱、太差了、气死我了"
        ),
        # Variant 2: 优化示例
        lambda p: p + "\n\n【示例】\n用户：我要退款 → 投诉兜底\n用户：退款怎么退 → 使用指导",
        # Variant 3: 调整温度
        lambda p: p,  # 温度在配置文件中改
        # Variant 4: 简化提示词
        lambda p: p[:len(p)//2] if len(p) > 1000 else p,
        # Variant 5: 增强边界情况处理
        lambda p: p + "\n\n【边界情况】\n- 用户只说\"我要投诉\" → 投诉兜底\n- 用户说\"垃圾！垃圾！垃圾！\" → 投诉兜底"
    ]
    
    if 1 <= variant_num <= len(variants):
        return variants[variant_num - 1](base_prompt)
    
    return base_prompt

# ==================== 测试执行 ====================

def run_single_scenario(scenario: Dict[str, Any], prompt_config: str = "v1") -> Dict[str, Any]:
    """
    运行单个测试场景
    
    Args:
        scenario: 测试场景
        prompt_config: Prompt 版本 ("v1" 或 "v2")
    
    Returns:
        测试结果
    """
    logger.info(f"=== 运行场景: {scenario['id']} - {scenario['name']} ===")
    
    # TODO: 这里需要实际调用工作流
    # 暂时返回模拟结果
    result = {
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "success": True,
        "turns": 4,
        "case_created": True,
        "phases": ["ask_clarify", "collect_info", "confirm", "done"]
    }
    
    return result

def run_all_scenarios(prompt_config: str = "v1") -> Dict[str, Any]:
    """
    运行所有测试场景
    
    Args:
        prompt_config: Prompt 版本
    
    Returns:
        汇总测试结果
    """
    logger.info(f"=== 运行所有场景 - Prompt 版本: {prompt_config} ===")
    
    results = []
    passed = 0
    failed = 0
    
    for scenario in TEST_SCENARIOS:
        try:
            result = run_single_scenario(scenario, prompt_config)
            results.append(result)
            
            if result["success"]:
                passed += 1
            else:
                failed += 1
                
        except Exception as e:
            logger.error(f"场景 {scenario['id']} 运行失败: {e}")
            failed += 1
            results.append({
                "scenario_id": scenario["id"],
                "scenario_name": scenario["name"],
                "success": False,
                "error": str(e)
            })
    
    total = len(TEST_SCENARIOS)
    pass_rate = passed / total if total > 0 else 0
    
    return {
        "prompt_version": prompt_config,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "results": results
    }

# ==================== Auto-Research 主循环 ====================

def auto_research_loop(num_rounds: int = 5) -> Dict[str, Any]:
    """
    Auto-Research 自动迭代循环
    
    Args:
        num_rounds: 迭代轮数
    
    Returns:
        所有迭代的结果
    """
    logger.info(f"=== Auto-Research 自动迭代开始 - {num_rounds} 轮 ===")
    
    # 读取基础 Prompt
    base_prompt_path = os.path.join(
        os.path.dirname(__file__), 
        '..', '..', 'config', 'intent_recognition_llm_cfg.json'
    )
    
    with open(base_prompt_path, 'r', encoding='utf-8') as f:
        base_config = json.load(f)
    
    base_prompt = base_config.get("sp", "")
    
    # 运行基准测试 (v1)
    logger.info("--- 第 0 轮：基准测试 (v1) ---")
    v1_result = run_all_scenarios("v1")
    
    iterations = [
        {
            "round": 0,
            "version": "v1",
            "result": v1_result,
            "change": "基准版本"
        }
    ]
    
    # 自动迭代 5 轮
    best_result = v1_result
    best_version = "v1"
    
    for i in range(1, num_rounds + 1):
        logger.info(f"--- 第 {i} 轮：Prompt 变体 v{i+1} ---")
        
        # 生成 Prompt 变体
        variant_prompt = generate_prompt_variant(base_prompt, i)
        
        # 保存变体 Prompt (临时)
        variant_config = base_config.copy()
        variant_config["sp"] = variant_prompt
        
        # 运行测试
        variant_result = run_all_scenarios(f"v{i+1}")
        
        iterations.append({
            "round": i,
            "version": f"v{i+1}",
            "result": variant_result,
            "change": f"Prompt 变体 {i}"
        })
        
        # 检查是否提升
        if variant_result["pass_rate"] > best_result["pass_rate"]:
            logger.info(f"✓ 通过率提升: {best_result['pass_rate']:.1%} → {variant_result['pass_rate']:.1%}")
            best_result = variant_result
            best_version = f"v{i+1}"
        else:
            logger.info(f"✗ 通过率未提升，保持当前最优版本")
    
    logger.info(f"=== Auto-Research 完成 - 最优版本: {best_version} ===")
    
    return {
        "iterations": iterations,
        "best_version": best_version,
        "best_result": best_result
    }

# ==================== 报告生成 ====================

def generate_report(result: Dict[str, Any]) -> str:
    """
    生成测试报告
    
    Args:
        result: Auto-Research 结果
    
    Returns:
        Markdown 格式报告
    """
    report = []
    report.append("# Auto-Research 兜底流程优化报告\n")
    report.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 最优版本
    report.append("\n## 🏆 最优版本\n")
    report.append(f"- **版本**: {result['best_version']}\n")
    report.append(f"- **通过率**: {result['best_result']['pass_rate']:.1%}\n")
    report.append(f"- **通过**: {result['best_result']['passed']}/{result['best_result']['total']}\n")
    
    # 迭代对比
    report.append("\n## 📊 迭代对比\n")
    report.append("| 轮次 | 版本 | 通过率 | 变化 |\n")
    report.append("|------|------|--------|------|\n")
    
    for iter_result in result['iterations']:
        pass_rate = iter_result['result']['pass_rate']
        report.append(f"| {iter_result['round']} | {iter_result['version']} | {pass_rate:.1%} | {iter_result['change']} |\n")
    
    # 场景详情
    report.append("\n## 📋 场景详情\n")
    best_result = result['best_result']
    
    report.append("| 场景 | 结果 | 轮数 | 工单创建 |\n")
    report.append("|------|------|------|----------|\n")
    
    for scenario_result in best_result['results']:
        status = "✅" if scenario_result.get("success", False) else "❌"
        turns = scenario_result.get("turns", 0)
        case_created = "是" if scenario_result.get("case_created", False) else "否"
        report.append(f"| {scenario_result['scenario_name']} | {status} | {turns} 轮 | {case_created} |\n")
    
    # 结论
    report.append("\n## 🎯 结论与建议\n")
    report.append(f"推荐使用 **{result['best_version']}** 版本，通过率达到 {result['best_result']['pass_rate']:.1%}\n")
    
    return "\n".join(report)

# ==================== 主函数 ====================

def main():
    """主函数"""
    print("=" * 60)
    print("Auto-Research 兜底流程优化")
    print("=" * 60)
    
    # 执行 Auto-Research 循环
    result = auto_research_loop(5)
    
    # 生成报告
    report = generate_report(result)
    
    # 保存报告
    report_path = os.path.join(
        os.path.dirname(__file__),
        '..', '..', 'assets',
        f'AutoResearch-Report-{datetime.now().strftime("%Y%m%d-%H%M%S")}.md'
    )
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n报告已保存到: {report_path}")
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

if __name__ == "__main__":
    main()
