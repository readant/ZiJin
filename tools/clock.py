"""系统时间工具"""
from datetime import datetime
from tools.registry import registry


@registry.register(
    description="获取当前日期和时间",
    parameters={"type": "object", "properties": {}, "required": []},
    safety_level="safe",
)
def get_current_time() -> str:
    now = datetime.now()
    week_days = ["一", "二", "三", "四", "五", "六", "日"]
    return f"现在是{now.year}年{now.month}月{now.day}日 星期{week_days[now.weekday()]} {now.strftime('%H:%M')}"


@registry.register(
    description="获取当前日期",
    parameters={"type": "object", "properties": {}, "required": []},
    safety_level="safe",
)
def get_current_date() -> str:
    now = datetime.now()
    week_days = ["一", "二", "三", "四", "五", "六", "日"]
    return f"今天是{now.year}年{now.month}月{now.day}日 星期{week_days[now.weekday()]}"


@registry.register(
    description="获取当前时间戳",
    parameters={"type": "object", "properties": {}, "required": []},
    safety_level="safe",
)
def get_timestamp() -> str:
    return str(int(datetime.now().timestamp()))
