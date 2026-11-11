"""安全审计日志 - 记录所有工具调用"""
import json
import os
import time
from datetime import datetime
from config.settings import DATA_DIR


AUDIT_LOG_PATH = os.path.join(DATA_DIR, "audit.jsonl")
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB 自动轮转


class AuditLogger:
    def __init__(self, path: str = AUDIT_LOG_PATH):
        self.path = path
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    def log(self, *, name: str, arguments: dict, result: str,
            safety_level: str = "unknown", blocked: bool = False,
            error: str = ""):
        entry = {
            "ts": datetime.now().isoformat(),
            "tool": name,
            "args": arguments,
            "result": result[:500],
            "level": safety_level,
            "blocked": blocked,
            "error": error,
        }
        self._rotate_if_needed()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _rotate_if_needed(self):
        if os.path.exists(self.path) and os.path.getsize(self.path) > MAX_LOG_SIZE:
            rotated = self.path + f".{int(time.time())}"
            os.rename(self.path, rotated)

    def get_recent(self, n: int = 50) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        entries = []
        for line in lines[-n:]:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return entries

    def get_by_tool(self, tool_name: str, n: int = 50) -> list[dict]:
        return [e for e in self.get_recent(n * 5) if e.get("tool") == tool_name][-n:]

    def get_blocked(self, n: int = 50) -> list[dict]:
        return [e for e in self.get_recent(n * 5) if e.get("blocked")][-n:]

    def format_recent(self, n: int = 20) -> str:
        entries = self.get_recent(n)
        if not entries:
            return "暂无审计记录"
        lines = []
        for e in reversed(entries):
            tag = "[BLOCKED]" if e.get("blocked") else "[OK]"
            ts = e.get("ts", "?")[:19]
            tool = e.get("tool", "?")
            level = e.get("level", "?")
            args_str = json.dumps(e.get("args", {}), ensure_ascii=False)
            if len(args_str) > 80:
                args_str = args_str[:80] + "..."
            lines.append(f"{ts} {tag} {tool}({level}) {args_str}")
        return "\n".join(lines)


audit = AuditLogger()
