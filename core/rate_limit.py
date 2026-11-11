"""频率限制器 - 防止工具滥用"""
import time
from collections import defaultdict
from core.log import get_logger

log = get_logger("rate_limit")

DEFAULT_LIMITS = {
    "close_application": {"count": 3, "window": 60},
    "open_application": {"count": 5, "window": 60},
    "click_position": {"count": 10, "window": 60},
    "type_text": {"count": 10, "window": 60},
    "search_file": {"count": 5, "window": 120},
    "_default": {"count": 20, "window": 60},
}


class RateLimiter:
    def __init__(self, limits: dict = None):
        self.limits = limits or DEFAULT_LIMITS
        self._calls: dict[str, list[float]] = defaultdict(list)

    def check(self, tool_name: str) -> tuple[bool, str]:
        now = time.time()
        # 自定义 limits 可能不含 "_default"，三级兜底避免 KeyError
        limit = (self.limits.get(tool_name)
                 or self.limits.get("_default")
                 or {"count": 20, "window": 60})
        window = limit["window"]
        max_count = limit["count"]

        self._calls[tool_name] = [
            t for t in self._calls[tool_name] if now - t < window
        ]

        if len(self._calls[tool_name]) >= max_count:
            log.warning("工具 %s 触发频率限制: %d/%ds",
                        tool_name, max_count, window)
            return False, f"操作过于频繁，{window}秒内最多{max_count}次"

        self._calls[tool_name].append(now)
        return True, ""

    def reset(self, tool_name: str = None):
        if tool_name:
            self._calls.pop(tool_name, None)
        else:
            self._calls.clear()


rate_limiter = RateLimiter()
