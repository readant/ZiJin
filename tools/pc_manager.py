"""电脑管家工具系统 - 注册式架构"""
import os
import subprocess
import psutil
import pyautogui
import pyperclip
from datetime import datetime
from tools.registry import registry
from core.log import get_logger

log = get_logger("tools.pc")


@registry.register(
    description="获取电脑系统信息，包括CPU、内存、磁盘使用率等",
    parameters={"type": "object", "properties": {}, "required": []},
    safety_level="safe",
)
def get_system_info() -> str:
    info = {
        "CPU使用率": f"{psutil.cpu_percent(interval=0.1)}%",
        "内存使用率": f"{psutil.virtual_memory().percent}%",
        "内存可用": f"{psutil.virtual_memory().available / (1024**3):.1f} GB",
        "磁盘使用率": {},
    }
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            info["磁盘使用率"][part.mountpoint] = f"{usage.percent}%"
        except PermissionError:
            pass
    info["开机时间"] = datetime.fromtimestamp(
        psutil.boot_time()
    ).strftime("%Y-%m-%d %H:%M:%S")
    info["当前时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return str(info)


@registry.register(
    description="启动指定应用程序",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "应用程序名称或路径"},
        },
        "required": ["app_name"],
    },
    safety_level="moderate",
    required_confirm=True,
)
def open_application(app_name: str) -> str:
    try:
        os.startfile(app_name)
        return f"已启动: {app_name}"
    except FileNotFoundError:
        try:
            subprocess.Popen(["cmd", "/c", "start", "", app_name])
            return f"已尝试启动: {app_name}"
        except Exception as e:
            return f"启动失败: {e}"


@registry.register(
    description="关闭指定应用程序进程",
    parameters={
        "type": "object",
        "properties": {
            "process_name": {"type": "string", "description": "进程名称，如 notepad.exe"},
        },
        "required": ["process_name"],
    },
    safety_level="dangerous",
    required_confirm=True,
)
def close_application(process_name: str) -> str:
    try:
        subprocess.run(["taskkill", "/F", "/IM", process_name], capture_output=True)
        return f"已关闭: {process_name}"
    except Exception as e:
        return f"关闭失败: {e}"


@registry.register(
    description="模拟键盘输入指定文本（支持中文）",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要输入的文本"},
        },
        "required": ["text"],
    },
    safety_level="safe",
)
def type_text(text: str) -> str:
    try:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        return f"已输入: {text[:50]}..."
    except Exception as e:
        return f"输入失败: {e}"


@registry.register(
    description="模拟鼠标点击指定屏幕坐标",
    parameters={
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "屏幕X坐标"},
            "y": {"type": "integer", "description": "屏幕Y坐标"},
        },
        "required": ["x", "y"],
    },
    safety_level="moderate",
    required_confirm=True,
)
def click_position(x: int, y: int) -> str:
    try:
        pyautogui.click(x, y)
        return f"已点击坐标: ({x}, {y})"
    except Exception as e:
        return f"点击失败: {e}"


@registry.register(
    description="获取系统剪贴板内容",
    parameters={"type": "object", "properties": {}, "required": []},
    safety_level="safe",
)
def get_clipboard() -> str:
    try:
        return pyperclip.paste()
    except Exception:
        return "获取剪贴板失败"


@registry.register(
    description="将文本复制到系统剪贴板",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要复制的文本"},
        },
        "required": ["text"],
    },
    safety_level="safe",
)
def set_clipboard(text: str) -> str:
    try:
        pyperclip.copy(text)
        return f"已复制到剪贴板: {text[:50]}..."
    except Exception:
        return "复制失败"


@registry.register(
    description="在指定路径搜索文件",
    parameters={
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "文件名关键词"},
            "search_path": {"type": "string", "description": "搜索路径，默认用户目录"},
        },
        "required": ["keyword"],
    },
    safety_level="moderate",
    required_confirm=True,
)
def search_file(keyword: str, search_path: str = None) -> str:
    if search_path is None:
        search_path = os.path.expanduser("~")
    results = []
    try:
        for root, dirs, files in os.walk(search_path):
            for f in files:
                if keyword.lower() in f.lower():
                    results.append(os.path.join(root, f))
                    if len(results) >= 10:
                        break
            if len(results) >= 10:
                break
    except PermissionError:
        pass
    if results:
        return "找到的文件:\n" + "\n".join(results)
    return f"未找到包含 '{keyword}' 的文件"


@registry.register(
    description="设置定时提醒",
    parameters={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "提醒内容"},
            "minutes": {"type": "integer", "description": "多少分钟后提醒(1-1440)"},
        },
        "required": ["message", "minutes"],
    },
    safety_level="safe",
)
def set_reminder(message: str, minutes: int) -> str:
    import threading
    import time

    def _remind():
        time.sleep(minutes * 60)
        log.info("[提醒] %s", message)

    t = threading.Thread(target=_remind, daemon=True)
    t.start()
    return f"已设置 {minutes} 分钟后的提醒: {message}"
