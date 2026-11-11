"""
事件总线模块 - 组件间解耦通信

原理：
    事件总线是一种发布-订阅模式的实现，用于解耦模块间的通信。
    模块A不需要知道模块B的存在，只需要发送事件，订阅了该事件的模块B会自动收到通知。

使用场景：
    - Agent 回复 -> UI 显示
    - 工具调用 -> 日志记录
    - 用户输入 -> 记忆存储
"""
from typing import Callable, Any
from collections import defaultdict
from core.log import get_logger

log = get_logger("bus")


class EventBus:
    """
    轻量级事件总线

    支持功能：
    - on(): 注册事件处理器
    - emit(): 触发事件
    - once(): 注册一次性处理器
    - off(): 移除处理器
    - clear(): 清空所有处理器
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def on(self, event: str, handler: Callable):
        self._handlers[event].append(handler)
        return lambda: self._handlers[event].remove(handler)

    def emit(self, event: str, *args, **kwargs):
        for handler in self._handlers.get(event, []):
            try:
                handler(*args, **kwargs)
            except Exception as e:
                log.error("Event '%s' handler error: %s", event, e)

    def once(self, event: str, handler: Callable):
        def wrapper(*args, **kwargs):
            self._handlers[event].remove(wrapper)
            handler(*args, **kwargs)
        self._handlers[event].append(wrapper)

    def off(self, event: str, handler: Callable = None):
        if handler is None:
            self._handlers.pop(event, None)
        elif handler in self._handlers[event]:
            self._handlers[event].remove(handler)

    def clear(self):
        self._handlers.clear()


bus = EventBus()
