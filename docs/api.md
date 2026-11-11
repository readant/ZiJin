# API 文档

本文档描述子衿项目的主要模块和公共接口。

## 核心模块

### Agent (`core/agent.py`)

Agent 是系统的核心协调器，负责处理用户输入、调用 LLM、执行工具和管理记忆。

#### 类：Agent

```python
class Agent:
    def __init__(self)
    def chat(self, user_input: str) -> dict
    def chat_stream(self, user_input: str) -> Generator[dict, None, None]
    def get_memory_stats(self) -> dict
    def clear_memory(self) -> None
```

**方法说明：**

- `chat(user_input: str) -> dict`
  - 同步对话接口
  - 参数：`user_input` - 用户输入文本
  - 返回：`{"emotion": "情感标签", "text": "回复文本", "tool_calls": [...], "tool_results": [...]}`

- `chat_stream(user_input: str) -> Generator[dict, None, None]`
  - 流式对话接口
  - 参数：`user_input` - 用户输入文本
  - 生成：`{"type": "text|emotion|tool_call|tool_result|done", "content": "...", ...}`

- `get_memory_stats() -> dict`
  - 获取记忆系统统计信息

- `clear_memory() -> None`
  - 清空短期记忆

---

### LLM Client (`core/llm.py`)

封装不同 LLM 提供商的 API 调用，提供统一接口。

#### 类：LLMClient

```python
class LLMClient:
    def __init__(self)
    def chat(self, messages: list[dict], tools: list[dict] = None) -> dict
    def chat_stream(self, messages: list[dict], tools: list[dict] = None) -> Generator[dict, None, None]
```

**方法说明：**

- `chat(messages, tools) -> dict`
  - 发送对话请求（同步）
  - 参数：
    - `messages`: 消息列表，格式 `[{"role": "user", "content": "..."}]`
    - `tools`: 工具定义列表（可选）
  - 返回：`{"content": "回复文本", "tool_calls": [...]}`

- `chat_stream(messages, tools) -> Generator`
  - 发送对话请求（流式）
  - 生成：`{"content": "文本片段", "done": False}`

---

### Memory Manager (`core/memory/manager.py`)

统一记忆管理器，协调三层记忆系统。

#### 类：MemoryManager

```python
class MemoryManager:
    def __init__(self)
    def add_conversation(self, role: str, content: str) -> None
    def build_context(self, current_query: str = None) -> list[dict]
    def clear_short(self) -> None
    def clear_long(self) -> None
    def clear_all(self) -> None
    def get_stats(self) -> dict
    def get_viewer(self) -> MemoryViewer
```

**方法说明：**

- `add_conversation(role, content) -> None`
  - 添加对话到记忆系统
  - 参数：
    - `role`: "user" 或 "assistant"
    - `content`: 消息内容

- `build_context(current_query) -> list[dict]`
  - 构建 LLM 上下文
  - 参数：`current_query` - 当前用户查询（用于检索相关记忆）
  - 返回：消息列表，可直接用于 LLM

- `get_stats() -> dict`
  - 获取记忆统计信息

- `get_viewer() -> MemoryViewer`
  - 获取记忆查看器（用于 UI 显示）

---

### Tool Executor (`core/tool_executor.py`)

处理工具调用的安全验证、执行和审计。

#### 类：ToolExecutor

```python
class ToolExecutor:
    def __init__(self)
    def execute_calls(self, tool_calls: list[dict], messages: list[dict]) -> tuple[list[dict], list[dict]]
    def confirm_pending(self, confirmed: bool) -> str | None
    def cleanup_async_tasks(self) -> None
```

**方法说明：**

- `execute_calls(tool_calls, messages) -> tuple[list[dict], list[dict]]`
  - 执行工具调用列表
  - 参数：
    - `tool_calls`: 工具调用列表
    - `messages`: 消息列表（用于添加工具结果）
  - 返回：`(all_calls, all_results)`

- `confirm_pending(confirmed) -> str | None`
  - 确认待执行的工具调用
  - 参数：`confirmed` - 是否确认执行

---

### Tool Registry (`tools/registry.py`)

工具注册表，支持装饰器式注册和 LLM function calling 格式生成。

#### 类：ToolRegistry

```python
class ToolRegistry:
    def __init__(self)
    def register(self, name: str = None, description: str = "",
                 parameters: dict = None, safety_level: str = "safe",
                 required_confirm: bool = False) -> Callable
    def execute(self, name: str, arguments: dict) -> str
    def definitions_for_llm(self) -> list[dict]
    def list_tools(self) -> list[str]
    def get_safety(self, name: str) -> str
```

**装饰器说明：**

```python
@registry.register(
    name="tool_name",
    description="工具描述",
    parameters={
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "参数描述"}
        },
        "required": ["param"]
    },
    safety_level="safe",  # safe/moderate/dangerous
    required_confirm=False
)
def my_tool(param: str) -> str:
    """工具实现"""
    return "结果"
```

---

## UI 模块

### Main Window (`ui/main_window.py`)

主窗口，包含 Live2D 渲染、聊天气泡、输入框和系统托盘。

#### 类：MainWindow

```python
class MainWindow(QMainWindow):
    def __init__(self, agent, model_path: str)
    def show_reply(self, emotion: str, text: str) -> None
    def on_user_input(self, text: str) -> None
```

---

### Components (`ui/components/`)

可复用 UI 组件：

- `BaseFloatingWidget`: 浮动窗口基类
- `Live2DWidget`: Live2D 渲染组件
- `ChatBubble`: 聊天气泡组件

---

### Widgets (`ui/widgets/`)

功能小部件：

- `MemoWidget`: 备忘录小部件
- `TodoWidget`: 待办清单小部件
- `MemoryWidget`: 记忆查看小部件
- `AuditWidget`: 审计日志小部件

---

### Workers (`ui/workers/`)

工作线程：

- `LLMWorker`: LLM 工作线程，支持流式输出

---

## 配置模块

### Settings (`config/settings.py`)

全局配置，支持环境变量覆盖。

**主要配置项：**

```python
# LLM 配置
LLM_PROVIDER = "ollama"  # 或 "openai_api"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b-instruct"
OPENAI_API_KEY = "your_key_here"
OPENAI_MODEL = "gpt-3.5-turbo"

# 记忆配置
SHORT_MEMORY_ROUNDS = 10
CHROMA_DB_PATH = "data/chroma_db"
CHROMA_COLLECTION = "zijin_memory"

# UI 配置
WINDOW_WIDTH = 350
WINDOW_HEIGHT = 500
WINDOW_OPACITY = 0.95

# TTS 配置
TTS_ENABLED = True
TTS_RATE = 150
TTS_VOLUME = 0.9
```

---

## 事件系统

### Event Bus (`core/bus.py`)

事件总线，用于模块间解耦通信。

**主要事件：**

- `user_message`: 用户消息
- `agent_reply`: Agent 回复
- `tool_call`: 工具调用
- `tool_result`: 工具结果

**使用方法：**

```python
from core.bus import bus

# 发送事件
bus.emit("user_message", "你好")

# 监听事件
@bus.on("agent_reply")
def handle_reply(emotion, text):
    print(f"收到回复: {text}")
```

---

## 工具模块

### 已注册工具

| 工具名称 | 描述 | 安全级别 |
|----------|------|----------|
| `get_current_time` | 获取当前时间 | safe |
| `get_current_date` | 获取当前日期 | safe |
| `get_timestamp` | 获取时间戳 | safe |
| `add_memo` | 添加备忘录 | safe |
| `list_memos` | 列出备忘录 | safe |
| `delete_memo` | 删除备忘录 | safe |
| `clear_memos` | 清空备忘录 | safe |
| `add_todo` | 添加待办 | safe |
| `list_todos` | 列出待办 | safe |
| `complete_todo` | 完成待办 | safe |
| `delete_todo` | 删除待办 | safe |
| `clear_todos` | 清空待办 | safe |
| `get_volume` | 获取音量 | safe |
| `set_volume` | 设置音量 | moderate |
| `toggle_mute` | 切换静音 | safe |
| `speak` | 语音合成 | safe |
| `speak_async` | 异步语音合成 | safe |
| `get_system_info` | 获取系统信息 | safe |
| `open_application` | 打开应用 | moderate |
| `close_application` | 关闭应用 | dangerous |
| `type_text` | 输入文本 | moderate |
| `click_position` | 点击位置 | moderate |
| `get_clipboard` | 获取剪贴板 | safe |
| `set_clipboard` | 设置剪贴板 | safe |
| `search_file` | 搜索文件 | moderate |
| `set_reminder` | 设置提醒 | moderate |