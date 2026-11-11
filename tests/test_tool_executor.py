"""单元测试 - 工具执行器（使用mock）"""
import sys
import os
import json
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_executor import ToolExecutor


def test_execute_safe_tool():
    executor = ToolExecutor()
    mock_response = {
        "function": {
            "name": "get_current_time",
            "arguments": "{}"
        },
        "id": "call_1"
    }

    with patch("core.tool_executor.registry") as mock_reg, \
         patch("core.tool_executor.rate_limiter") as mock_rl, \
         patch("core.tool_executor.audit"):
        mock_reg.get_safety.return_value = "safe"
        mock_rl.check.return_value = (True, "")
        mock_reg.execute.return_value = "12:00:00"

        messages = []
        calls, results = executor.execute_calls([mock_response], messages)

        assert len(calls) == 1
        assert calls[0]["name"] == "get_current_time"
        assert results[0]["result"] == "12:00:00"
        assert len(messages) == 1
        assert messages[0]["role"] == "tool"


def test_blocked_by_rate_limit():
    executor = ToolExecutor()
    mock_response = {
        "function": {"name": "close_application", "arguments": '{"process_name": "test.exe"}'},
        "id": "call_1"
    }

    with patch("core.tool_executor.registry") as mock_reg, \
         patch("core.tool_executor.rate_limiter") as mock_rl, \
         patch("core.tool_executor.audit"):
        mock_reg.get_safety.return_value = "dangerous"
        mock_rl.check.return_value = (False, "过于频繁")

        messages = []
        calls, results = executor.execute_calls([mock_response], messages)

        assert results[0]["result"] == "过于频繁"
        mock_reg.execute.assert_not_called()


def test_blocked_by_safety():
    executor = ToolExecutor()
    mock_response = {
        "function": {"name": "search_file", "arguments": '{"search_path": "/etc"}'},
        "id": "call_1"
    }

    with patch("core.tool_executor.registry") as mock_reg, \
         patch("core.tool_executor.rate_limiter") as mock_rl, \
         patch("core.tool_executor.validate_tool_input") as mock_val, \
         patch("core.tool_executor.audit"):
        mock_reg.get_safety.return_value = "moderate"
        mock_rl.check.return_value = (True, "")
        mock_val.return_value = (False, "路径受限")

        messages = []
        calls, results = executor.execute_calls([mock_response], messages)

        assert "安全拒绝" in results[0]["result"]
        mock_reg.execute.assert_not_called()


def test_needs_confirmation():
    executor = ToolExecutor()
    mock_response = {
        "function": {"name": "close_application", "arguments": '{"process_name": "notepad.exe"}'},
        "id": "call_1"
    }

    with patch("core.tool_executor.registry") as mock_reg, \
         patch("core.tool_executor.rate_limiter") as mock_rl, \
         patch("core.tool_executor.needs_confirmation") as mock_nc, \
         patch("core.tool_executor.audit"):
        mock_reg.get_safety.return_value = "dangerous"
        mock_rl.check.return_value = (True, "")
        mock_nc.return_value = True

        messages = []
        calls, results = executor.execute_calls([mock_response], messages)

        assert "确认" in results[0]["result"]
        assert executor.pending_confirm is not None
        mock_reg.execute.assert_not_called()


def test_confirm_pending():
    executor = ToolExecutor()
    executor.pending_confirm = {"name": "close_application", "args": {"process_name": "x"}}

    with patch("core.tool_executor.registry") as mock_reg, \
         patch("core.tool_executor.rate_limiter") as mock_rl, \
         patch("core.tool_executor.validate_tool_input") as mock_val, \
         patch("core.tool_executor.audit"):
        mock_reg.get_safety.return_value = "dangerous"
        mock_rl.check.return_value = (True, "")
        mock_val.return_value = (True, "")
        mock_reg.execute.return_value = "done"

        result = executor.confirm_pending(True)

        assert result == "done"
        assert executor.pending_confirm is None
        mock_reg.execute.assert_called_once()
