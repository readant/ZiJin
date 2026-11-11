"""审计日志功能测试"""
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.audit import AuditLogger

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_audit_result.txt")

def log(msg):
    # 仅在直接运行本文件时写结果文件，避免 pytest 收集用例时污染项目根目录
    if __name__ == "__main__":
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

def test_log_write_and_read():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        tmp_path = f.name
    try:
        logger = AuditLogger(path=tmp_path)

        logger.log(name="test_tool", arguments={"key": "val"}, result="ok",
                    safety_level="safe")
        logger.log(name="dangerous_tool", arguments={"cmd": "rm -rf /"}, result="blocked",
                    safety_level="dangerous", blocked=True, error="bad cmd")

        entries = logger.get_recent(10)
        assert len(entries) == 2, f"expected 2 got {len(entries)}"
        assert entries[0]["tool"] == "test_tool"
        assert entries[0]["blocked"] is False
        assert entries[1]["tool"] == "dangerous_tool"
        assert entries[1]["blocked"] is True
        assert entries[1]["error"] == "bad cmd"
        log("[PASS] test_log_write_and_read")
    finally:
        os.unlink(tmp_path)


def test_get_blocked():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        tmp_path = f.name
    try:
        logger = AuditLogger(path=tmp_path)

        logger.log(name="tool_a", arguments={}, result="ok")
        logger.log(name="tool_b", arguments={}, result="no", blocked=True, error="bad")
        logger.log(name="tool_c", arguments={}, result="ok")

        blocked = logger.get_blocked()
        assert len(blocked) == 1
        assert blocked[0]["tool"] == "tool_b"
        log("[PASS] test_get_blocked")
    finally:
        os.unlink(tmp_path)


def test_get_by_tool():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        tmp_path = f.name
    try:
        logger = AuditLogger(path=tmp_path)

        logger.log(name="alpha", arguments={}, result="1")
        logger.log(name="beta", arguments={}, result="2")
        logger.log(name="alpha", arguments={}, result="3")

        alpha = logger.get_by_tool("alpha")
        assert len(alpha) == 2
        assert all(e["tool"] == "alpha" for e in alpha)
        log("[PASS] test_get_by_tool")
    finally:
        os.unlink(tmp_path)


def test_format_recent():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        tmp_path = f.name
    try:
        logger = AuditLogger(path=tmp_path)

        text = logger.format_recent()
        assert text == "\u6682\u65e0\u5ba1\u8ba1\u8bb0\u5f55"

        logger.log(name="my_tool", arguments={"a": 1}, result="done",
                   safety_level="safe")
        text = logger.format_recent()
        assert "[OK]" in text
        assert "my_tool" in text
        assert "safe" in text
        log("[PASS] test_format_recent")
    finally:
        os.unlink(tmp_path)


def test_result_truncation():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        tmp_path = f.name
    try:
        logger = AuditLogger(path=tmp_path)

        long_result = "x" * 1000
        logger.log(name="tool", arguments={}, result=long_result)

        entries = logger.get_recent(1)
        assert len(entries[0]["result"]) == 500
        log("[PASS] test_result_truncation")
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    if os.path.exists(LOG_FILE):
        os.unlink(LOG_FILE)

    tests = [test_log_write_and_read, test_get_blocked, test_get_by_tool,
             test_format_recent, test_result_truncation]
    ok = 0
    for t in tests:
        try:
            t()
            ok += 1
        except Exception as e:
            log(f"[FAIL] {t.__name__}: {e}")
    log(f"\nResult: {ok}/{len(tests)} passed")
