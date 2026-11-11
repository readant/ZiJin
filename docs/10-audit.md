# 安全审计日志

## 原理

记录所有工具调用，用于安全审计和问题排查。

```
Agent执行工具
       │
       ▼
┌──────────────┐
│ Safety       │  安全验证
│ .validate()  │
└──────┬───────┘
       │
       ├─── 通过 ──→ 执行工具 ──→ audit.log(blocked=False)
       │
       └─── 拦截 ──→ audit.log(blocked=True, error=原因)
```

## 实现

### 日志格式

每条记录为一行 JSON（JSONL 格式）：

```json
{
  "ts": "2026-07-04T13:28:16.123456",
  "tool": "close_application",
  "args": {"process_name": "notepad.exe"},
  "result": "已关闭: notepad.exe",
  "level": "dangerous",
  "blocked": false,
  "error": ""
}
```

| 字段 | 说明 |
|------|------|
| `ts` | ISO 8601 时间戳 |
| `tool` | 工具名称 |
| `args` | 调用参数 |
| `result` | 执行结果（截断到 500 字符） |
| `level` | 安全级别：`safe` / `moderate` / `dangerous` |
| `blocked` | 是否被安全层拦截 |
| `error` | 拦截原因（仅 blocked 时有值） |

### 核心类

```python
class AuditLogger:
    def __init__(self, path=DATA_DIR + "/audit.jsonl"):
        ...

    def log(self, *, name, arguments, result,
            safety_level="unknown", blocked=False, error=""):
        # 写入一条审计记录

    def get_recent(self, n=50) -> list[dict]:
        # 获取最近 n 条记录

    def get_by_tool(self, tool_name, n=50) -> list[dict]:
        # 按工具名筛选

    def get_blocked(self, n=50) -> list[dict]:
        # 仅获取被拦截的记录

    def format_recent(self, n=20) -> str:
        # 格式化为可读文本
```

### 集成点

在 `core/agent.py` 的工具执行循环中调用：

```python
safety = registry.get_safety(name)
valid, err = validate_tool_input(name, args)

if not valid:
    result = f"安全拒绝: {err}"
    audit.log(name=name, arguments=args, result=result,
              safety_level=safety, blocked=True, error=err)
else:
    result = registry.execute(name, args)
    audit.log(name=name, arguments=args, result=result,
              safety_level=safety)
```

## 存储与轮转

- 存储路径：`data/audit.jsonl`
- 格式：JSONL（每行一条 JSON，追加写入）
- 自动轮转：文件超过 10MB 时重命名为 `audit.jsonl.<timestamp>`
- 已在 `.gitignore` 中排除

## UI 查看

右键菜单或系统托盘 → **审计日志**，打开 `AuditWidget`：

- 显示最近 30 条记录
- 「仅看拦截」按钮过滤被安全层拒绝的调用
- 每次工具调用后自动可刷新
