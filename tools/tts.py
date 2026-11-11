"""语音合成工具

支持口型同步：播放时通过事件总线通知 Live2D 组件驱动嘴型动画。
"""
import threading
from tools.registry import registry
from core.bus import bus
from config.settings import TTS_ENABLED, TTS_RATE, TTS_VOLUME, TTS_VOICE_INDEX


@registry.register(
    description="将文本转换为语音播放",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要朗读的文本"},
        },
        "required": ["text"],
    },
    safety_level="safe",
)
def speak(text: str) -> str:
    if not TTS_ENABLED:
        return "语音功能未启用"
    try:
        import pyttsx3
        bus.emit("tts_start")
        engine = pyttsx3.init()
        engine.setProperty("rate", TTS_RATE)
        engine.setProperty("volume", TTS_VOLUME)
        voices = engine.getProperty("voices")
        if voices and TTS_VOICE_INDEX < len(voices):
            engine.setProperty("voice", voices[TTS_VOICE_INDEX].id)
        engine.say(text)
        engine.runAndWait()
        bus.emit("tts_end")
        return f"已朗读：{text[:30]}..."
    except Exception:
        bus.emit("tts_end")
        return "语音合成失败，请检查pyttsx3是否安装"


@registry.register(
    description="将文本转换为语音（后台播放，不阻塞）",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要朗读的文本"},
        },
        "required": ["text"],
    },
    safety_level="safe",
)
def speak_async(text: str) -> str:
    if not TTS_ENABLED:
        return "语音功能未启用"
    try:
        import pyttsx3

        def _speak():
            bus.emit("tts_start")
            engine = pyttsx3.init()
            engine.setProperty("rate", TTS_RATE)
            engine.setProperty("volume", TTS_VOLUME)
            voices = engine.getProperty("voices")
            if voices and TTS_VOICE_INDEX < len(voices):
                engine.setProperty("voice", voices[TTS_VOICE_INDEX].id)
            engine.say(text)
            engine.runAndWait()
            bus.emit("tts_end")

        threading.Thread(target=_speak, daemon=True).start()
        return f"已开始朗读：{text[:30]}..."
    except Exception:
        bus.emit("tts_end")
        return "语音合成失败，请检查pyttsx3是否安装"
