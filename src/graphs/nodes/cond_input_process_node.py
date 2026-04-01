"""
条件判断节点 - 语音输入判断
"""
from graphs.state import VoiceInputCheck


def cond_input_process(state: VoiceInputCheck) -> str:
    """
    title: 语音输入判断
    desc: 判断是否有语音输入，决定是否需要 ASR 处理
    """
    if state.voice_url and state.voice_url.strip():
        return "语音处理"
    else:
        return "直接处理文字"
