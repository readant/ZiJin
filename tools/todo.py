"""待办清单工具"""
import json
import os
from datetime import datetime
from tools.registry import registry
from config.settings import TODO_PATH


def _load_todos() -> list[dict]:
    if os.path.exists(TODO_PATH):
        with open(TODO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_todos(todos: list[dict]):
    os.makedirs(os.path.dirname(TODO_PATH), exist_ok=True)
    with open(TODO_PATH, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


@registry.register(
    description="添加一条待办事项",
    parameters={
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "待办内容"},
            "priority": {"type": "string", "description": "优先级：high/medium/low，默认medium"},
            "due_date": {"type": "string", "description": "截止日期，格式：YYYY-MM-DD"},
        },
        "required": ["task"],
    },
    safety_level="safe",
)
def add_todo(task: str, priority: str = "medium", due_date: str = None) -> str:
    todos = _load_todos()
    todo = {
        "id": len(todos) + 1,
        "task": task,
        "priority": priority,
        "due_date": due_date,
        "completed": False,
        "created_at": datetime.now().isoformat(),
    }
    todos.append(todo)
    _save_todos(todos)
    return f"已添加待办：{task}"


@registry.register(
    description="查看所有待办事项",
    parameters={
        "type": "object",
        "properties": {
            "show_completed": {"type": "boolean", "description": "是否显示已完成的，默认false"},
        },
        "required": [],
    },
    safety_level="safe",
)
def list_todos(show_completed: bool = False) -> str:
    todos = _load_todos()
    if not show_completed:
        todos = [t for t in todos if not t.get("completed")]
    if not todos:
        return "暂无待办事项"
    lines = []
    priority_map = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    for t in todos:
        status = "✓" if t.get("completed") else "○"
        pri = priority_map.get(t.get("priority", "medium"), "🟡")
        due = f" (截止:{t['due_date']})" if t.get("due_date") else ""
        lines.append(f"{status} {pri} {t['task']}{due}")
    return "待办清单：\n" + "\n".join(lines)


@registry.register(
    description="标记待办事项为已完成",
    parameters={
        "type": "object",
        "properties": {
            "todo_id": {"type": "integer", "description": "待办ID"},
        },
        "required": ["todo_id"],
    },
    safety_level="safe",
)
def complete_todo(todo_id: int) -> str:
    todos = _load_todos()
    for t in todos:
        if t.get("id") == todo_id:
            t["completed"] = True
            _save_todos(todos)
            return f"已完成待办：{t['task']}"
    return f"未找到ID为{todo_id}的待办"


@registry.register(
    description="删除一条待办事项",
    parameters={
        "type": "object",
        "properties": {
            "todo_id": {"type": "integer", "description": "待办ID"},
        },
        "required": ["todo_id"],
    },
    safety_level="safe",
)
def delete_todo(todo_id: int) -> str:
    todos = _load_todos()
    for i, t in enumerate(todos):
        if t.get("id") == todo_id:
            deleted = todos.pop(i)
            _save_todos(todos)
            return f"已删除待办：{deleted['task']}"
    return f"未找到ID为{todo_id}的待办"


@registry.register(
    description="清空所有待办事项",
    parameters={"type": "object", "properties": {}, "required": []},
    safety_level="moderate",
    required_confirm=True,
)
def clear_todos() -> str:
    _save_todos([])
    return "已清空所有待办事项"
