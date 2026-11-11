"""备忘录工具"""
import json
import os
from datetime import datetime
from tools.registry import registry
from config.settings import MEMO_PATH


def _load_memos() -> list[dict]:
    if os.path.exists(MEMO_PATH):
        with open(MEMO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_memos(memos: list[dict]):
    os.makedirs(os.path.dirname(MEMO_PATH), exist_ok=True)
    with open(MEMO_PATH, "w", encoding="utf-8") as f:
        json.dump(memos, f, ensure_ascii=False, indent=2)


@registry.register(
    description="添加一条备忘录",
    parameters={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "备忘内容"},
            "category": {"type": "string", "description": "分类，默认为'通用'"},
        },
        "required": ["content"],
    },
    safety_level="safe",
)
def add_memo(content: str, category: str = "通用") -> str:
    memos = _load_memos()
    memo = {
        "id": len(memos) + 1,
        "content": content,
        "category": category,
        "created_at": datetime.now().isoformat(),
        "completed": False,
    }
    memos.append(memo)
    _save_memos(memos)
    return f"已记录备忘：{content}"


@registry.register(
    description="查看所有备忘录",
    parameters={
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "按分类筛选，不传则查看全部"},
        },
        "required": [],
    },
    safety_level="safe",
)
def list_memos(category: str = None) -> str:
    memos = _load_memos()
    if category:
        memos = [m for m in memos if m.get("category") == category]
    if not memos:
        return "暂无备忘录"
    lines = []
    for m in memos:
        status = "✓" if m.get("completed") else "○"
        lines.append(f"{status} [{m['category']}] {m['content']}")
    return "备忘录列表：\n" + "\n".join(lines)


@registry.register(
    description="删除一条备忘录",
    parameters={
        "type": "object",
        "properties": {
            "memo_id": {"type": "integer", "description": "备忘录ID"},
        },
        "required": ["memo_id"],
    },
    safety_level="safe",
)
def delete_memo(memo_id: int) -> str:
    memos = _load_memos()
    for i, m in enumerate(memos):
        if m.get("id") == memo_id:
            deleted = memos.pop(i)
            _save_memos(memos)
            return f"已删除备忘：{deleted['content']}"
    return f"未找到ID为{memo_id}的备忘录"


@registry.register(
    description="清空所有备忘录",
    parameters={"type": "object", "properties": {}, "required": []},
    safety_level="moderate",
    required_confirm=True,
)
def clear_memos() -> str:
    _save_memos([])
    return "已清空所有备忘录"
