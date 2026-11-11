"""
安全层 - 工具执行权限控制与输入验证

原理：
    在执行工具前验证输入参数，防止危险操作。
    如：阻止删除系统文件、格式化磁盘等危险命令。
"""
import os
import re
from core.log import get_logger

log = get_logger("safety")

ALLOWED_SEARCH_ROOTS = [os.path.expanduser("~")]

BLOCKED_PATTERNS = [
    re.compile(r"rm\s+-rf", re.IGNORECASE),
    re.compile(r"format\s+[a-z]:", re.IGNORECASE),
    re.compile(r"del\s+/[sf]", re.IGNORECASE),
]

ALLOWED_EXTENSIONS = {
    "open_application": {".exe", ".bat", ".cmd", ".lnk"},
}


def validate_tool_input(name: str, arguments: dict) -> tuple[bool, str]:
    if name == "search_file":
        path = arguments.get("search_path", "")
        if path and not any(path.startswith(root) for root in ALLOWED_SEARCH_ROOTS):
            log.warning("搜索路径受限: %s", path)
            return False, f"搜索路径受限，仅允许: {ALLOWED_SEARCH_ROOTS}"
        if any(p.search(str(arguments)) for p in BLOCKED_PATTERNS):
            log.warning("输入包含危险命令模式: %s", arguments)
            return False, "输入包含危险命令模式"

    if name == "open_application":
        app = arguments.get("app_name", "")
        if any(p.search(app) for p in BLOCKED_PATTERNS):
            log.warning("打开应用包含危险命令: %s", app)
            return False, "输入包含危险命令模式"

    if name == "close_application":
        proc = arguments.get("process_name", "")
        if any(p.search(proc) for p in BLOCKED_PATTERNS):
            log.warning("关闭应用包含危险命令: %s", proc)
            return False, "输入包含危险命令模式"

    if name == "set_reminder":
        minutes = arguments.get("minutes", 0)
        if not isinstance(minutes, int) or minutes < 1 or minutes > 1440:
            return False, "提醒时间需在1-1440分钟之间"

    return True, ""


def needs_confirmation(name: str) -> bool:
    dangerous_tools = {"close_application", "search_file", "click_position"}
    return name in dangerous_tools
