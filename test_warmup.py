#!/usr/bin/env python3
"""
测试启动预热效果的脚本
模拟服务启动时的预热过程，统计各阶段耗时
"""
import os
import sys
import time
import logging
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_database_warmup() -> Dict[str, Any]:
    """
    测试数据库预热
    """
    logger.info("=" * 60)
    logger.info("[数据库预热测试]")
    logger.info("=" * 60)
    
    result = {
        "success": False,
        "elapsed": 0.0,
        "error": None
    }
    
    try:
        start_time = time.time()
        
        # 导入数据库模块
        from storage.database.db import get_engine
        from sqlalchemy import text
        
        # 获取引擎（这会触发连接池初始化）
        logger.info("1. 获取数据库引擎...")
        engine_start = time.time()
        engine = get_engine()
        engine_elapsed = time.time() - engine_start
        logger.info(f"   ✅ 引擎获取完成，耗时: {engine_elapsed:.3f}s")
        
        # 测试连接
        logger.info("2. 测试数据库连接...")
        conn_start = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        conn_elapsed = time.time() - conn_start
        logger.info(f"   ✅ 连接测试完成，耗时: {conn_elapsed:.3f}s")
        
        total_elapsed = time.time() - start_time
        result["success"] = True
        result["elapsed"] = total_elapsed
        
        logger.info("")
        logger.info(f"✅ 数据库预热成功！总耗时: {total_elapsed:.3f}s")
        logger.info(f"   - 引擎初始化: {engine_elapsed:.3f}s")
        logger.info(f"   - 连接测试: {conn_elapsed:.3f}s")
        
    except Exception as e:
        logger.error(f"❌ 数据库预热失败: {e}")
        result["error"] = str(e)
        import traceback
        logger.error(traceback.format_exc())
    
    return result


def test_graph_warmup() -> Dict[str, Any]:
    """
    测试图预热
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("[LangGraph 工作流预热测试]")
    logger.info("=" * 60)
    
    result = {
        "success": False,
        "elapsed": 0.0,
        "error": None
    }
    
    try:
        start_time = time.time()
        
        # 导入图模块
        logger.info("1. 导入图模块...")
        import_start = time.time()
        from graphs.graph import main_graph
        import_elapsed = time.time() - import_start
        logger.info(f"   ✅ 模块导入完成，耗时: {import_elapsed:.3f}s")
        
        # 图已经在导入时编译了，直接测试调用
        logger.info("2. 图已就绪（编译在导入时完成）")
        
        total_elapsed = time.time() - start_time
        result["success"] = True
        result["elapsed"] = total_elapsed
        
        logger.info("")
        logger.info(f"✅ LangGraph 工作流预热成功！总耗时: {total_elapsed:.3f}s")
        logger.info(f"   - 模块导入: {import_elapsed:.3f}s")
        
    except Exception as e:
        logger.error(f"❌ LangGraph 预热失败: {e}")
        result["error"] = str(e)
        import traceback
        logger.error(traceback.format_exc())
    
    return result


def test_full_workflow() -> Dict[str, Any]:
    """
    测试完整工作流调用（模拟第一次用户请求）
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("[完整工作流调用测试（模拟第一次用户请求）]")
    logger.info("=" * 60)
    
    result = {
        "success": False,
        "elapsed": 0.0,
        "error": None
    }
    
    try:
        start_time = time.time()
        
        # 测试工作流调用
        logger.info("1. 调用工作流...")
        from graphs.graph import main_graph
        from coze_coding_utils.runtime_ctx.context import new_context
        
        ctx = new_context(method="test_warmup")
        payload = {
            "user_message": "你好，这是预热测试",
            "user_id": "warmup_test_user_001"
        }
        
        workflow_start = time.time()
        
        # 同步调用工作流
        result_obj = main_graph.invoke(payload, context=ctx)
        
        workflow_elapsed = time.time() - workflow_start
        logger.info(f"   ✅ 工作流调用完成，耗时: {workflow_elapsed:.3f}s")
        logger.info(f"   📝 回复内容: {result_obj.get('reply_content', '')[:50]}...")
        
        total_elapsed = time.time() - start_time
        result["success"] = True
        result["elapsed"] = total_elapsed
        
        logger.info("")
        logger.info(f"✅ 完整工作流调用成功！总耗时: {total_elapsed:.3f}s")
        logger.info(f"   - 工作流调用: {workflow_elapsed:.3f}s")
        
    except Exception as e:
        logger.error(f"❌ 完整工作流调用失败: {e}")
        result["error"] = str(e)
        import traceback
        logger.error(traceback.format_exc())
    
    return result


def main():
    """
    主测试函数
    """
    logger.info("")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 10 + "🚀 启动预热效果测试 🚀" + " " * 20 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("")
    
    # 测试数据库预热
    db_result = test_database_warmup()
    
    # 测试图预热
    graph_result = test_graph_warmup()
    
    # 测试完整工作流
    workflow_result = test_full_workflow()
    
    # 总结
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 测试总结")
    logger.info("=" * 60)
    
    total_time = 0.0
    all_success = True
    
    if db_result["success"]:
        logger.info(f"✅ 数据库预热: {db_result['elapsed']:.3f}s")
        total_time += db_result["elapsed"]
    else:
        logger.info(f"❌ 数据库预热: 失败 - {db_result['error']}")
        all_success = False
    
    if graph_result["success"]:
        logger.info(f"✅ LangGraph 预热: {graph_result['elapsed']:.3f}s")
        total_time += graph_result["elapsed"]
    else:
        logger.info(f"❌ LangGraph 预热: 失败 - {graph_result['error']}")
        all_success = False
    
    if workflow_result["success"]:
        logger.info(f"✅ 工作流调用: {workflow_result['elapsed']:.3f}s")
    else:
        logger.info(f"❌ 工作流调用: 失败 - {workflow_result['error']}")
        all_success = False
    
    logger.info("")
    logger.info(f"⏱️  预热总耗时: {total_time:.3f}s")
    logger.info("")
    
    if all_success:
        logger.info("🎉 所有预热测试通过！")
        logger.info("")
        logger.info("💡 预期效果：")
        logger.info("   - 服务启动时完成预热（耗时约 %.2fs）" % total_time)
        logger.info("   - 第一次用户请求时不再有明显的冷启动延迟")
        logger.info("   - 预期第一次请求响应时间 < 2秒")
    else:
        logger.warning("⚠️  部分预热测试失败，请检查错误信息")
    
    logger.info("")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
