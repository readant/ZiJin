"""音量控制工具"""
from tools.registry import registry


def _get_volume_interface():
    from pycaw.pycaw import AudioUtilities
    speakers = AudioUtilities.GetSpeakers()
    return speakers.EndpointVolume


@registry.register(
    description="获取当前系统音量",
    parameters={"type": "object", "properties": {}, "required": []},
    safety_level="safe",
)
def get_volume() -> str:
    try:
        volume = _get_volume_interface()
        level = volume.GetMasterVolumeLevelScalar()
        return f"当前音量：{int(level * 100)}%"
    except Exception:
        return "获取音量失败，请检查pycaw是否安装"


@registry.register(
    description="设置系统音量(0-100)",
    parameters={
        "type": "object",
        "properties": {
            "level": {"type": "integer", "description": "音量级别，0-100"},
        },
        "required": ["level"],
    },
    safety_level="safe",
)
def set_volume(level: int) -> str:
    if not 0 <= level <= 100:
        return "音量需在0-100之间"
    try:
        volume = _get_volume_interface()
        volume.SetMasterVolumeLevelScalar(level / 100, None)
        return f"已设置音量为：{level}%"
    except Exception:
        return "设置音量失败，请检查pycaw是否安装"


@registry.register(
    description="静音/取消静音",
    parameters={"type": "object", "properties": {}, "required": []},
    safety_level="safe",
)
def toggle_mute() -> str:
    try:
        volume = _get_volume_interface()
        current = volume.GetMute()
        volume.SetMute(not current, None)
        return "已取消静音" if current else "已静音"
    except Exception:
        return "操作失败，请检查pycaw是否安装"
