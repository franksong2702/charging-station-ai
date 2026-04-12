"""
Utils Log Loop Trace 模块
用于兼容 coze_coding_utils 的导入
"""

# 重定向到正确的导入
from coze_coding_utils.log.loop_trace import init_agent_config, init_run_config

__all__ = ['init_agent_config', 'init_run_config']
