"""单元测试 - 频率限制器"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rate_limit import RateLimiter


def test_first_call_allowed():
    limiter = RateLimiter(limits={"test": {"count": 3, "window": 60}})
    allowed, msg = limiter.check("test")
    assert allowed is True
    assert msg == ""


def test_rate_limit_triggered():
    limiter = RateLimiter(limits={"test": {"count": 2, "window": 60}})
    limiter.check("test")
    limiter.check("test")
    allowed, msg = limiter.check("test")
    assert allowed is False
    assert "频繁" in msg


def test_different_tools_independent():
    limiter = RateLimiter(limits={
        "a": {"count": 1, "window": 60},
        "b": {"count": 10, "window": 60},
    })
    limiter.check("a")
    allowed_a, _ = limiter.check("a")
    allowed_b, _ = limiter.check("b")
    assert allowed_a is False
    assert allowed_b is True


def test_reset():
    limiter = RateLimiter(limits={"test": {"count": 1, "window": 60}})
    limiter.check("test")
    limiter.reset("test")
    allowed, _ = limiter.check("test")
    assert allowed is True
