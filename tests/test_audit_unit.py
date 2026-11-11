"""单元测试 - 审计日志"""
import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.audit import AuditLogger


def test_log_write_read():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        tmp = f.name
    try:
        logger = AuditLogger(path=tmp)
        logger.log(name="test", arguments={"k": "v"}, result="ok")
        entries = logger.get_recent(10)
        assert len(entries) == 1
        assert entries[0]["tool"] == "test"
        assert entries[0]["blocked"] is False
    finally:
        os.unlink(tmp)


def test_blocked_logging():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        tmp = f.name
    try:
        logger = AuditLogger(path=tmp)
        logger.log(name="bad", arguments={}, result="no",
                   safety_level="dangerous", blocked=True, error="reason")
        blocked = logger.get_blocked()
        assert len(blocked) == 1
        assert blocked[0]["error"] == "reason"
    finally:
        os.unlink(tmp)


def test_result_truncation():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        tmp = f.name
    try:
        logger = AuditLogger(path=tmp)
        logger.log(name="t", arguments={}, result="x" * 1000)
        entries = logger.get_recent(1)
        assert len(entries[0]["result"]) == 500
    finally:
        os.unlink(tmp)


def test_format_recent_empty():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        tmp = f.name
    try:
        logger = AuditLogger(path=tmp)
        text = logger.format_recent()
        assert text == "\u6682\u65e0\u5ba1\u8ba1\u8bb0\u5f55"
    finally:
        os.unlink(tmp)


def test_format_recent_content():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        tmp = f.name
    try:
        logger = AuditLogger(path=tmp)
        logger.log(name="my_tool", arguments={"a": 1}, result="done")
        text = logger.format_recent()
        assert "[OK]" in text
        assert "my_tool" in text
    finally:
        os.unlink(tmp)
