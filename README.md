# 子衿 · 桌面伴生代理

> 青青子衿，悠悠我心

一个基于 **PyQt6 + Live2D** 的 Windows 桌面虚拟伴侣：本地大模型对话、情感驱动的角色表情、三层记忆系统，以及 26 个可直接操作电脑的桌面工具。

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-41CD52?logo=qt&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 特性

### 对话与人格

- **双后端 LLM** — Ollama（本地，默认 `qwen2.5:7b-instruct`）与 OpenAI 兼容 API 可切换
- **流式输出** — 逐字渲染，不阻塞界面
- **情感驱动** — 10 种情感标签 + 肢体参数协议，直接映射到 Live2D 动作与姿态

LLM 按约定在回复首部输出标签，程序解析后同时驱动气泡配色与角色动画：

```text
[happy,head_tilt=8] 太好了，我陪你一起开心
[sad,body_lean=-10] 今天辛苦了，先歇一会儿吧
```

### 三层记忆

| 层级 | 实现 | 作用 |
|---|---|---|
| 短期记忆 | 内存列表，保留最近 N 轮 | 维持对话连贯 |
| 长期记忆 | ChromaDB 向量检索 + 重要性打分 + 去重 | 跨会话回忆 |
| 用户画像 | JSON 持久化 | 姓名、偏好、事实 |

长期记忆采用**后台预热 + 未就绪降级**：嵌入模型不可用时自动跳过向量操作，绝不阻塞对话（详见[已知限制](#已知限制)）。

### 桌面工具（26 个）

时间日期、备忘录、待办、音量与静音、TTS 朗读（带口型同步）、系统信息、应用启停、键鼠模拟、剪贴板、文件搜索、定时提醒。

所有工具调用都经过统一流水线：

```text
限流 → 安全校验 → 用户确认（危险操作） → 执行 → 审计落盘
```

### 交互

| 操作 | 效果 |
|---|---|
| 拖拽 | 移动窗口 |
| 双击 | 展开/收起对话输入 |
| 右键 | 圆环菜单（对话 / 备忘录 / 待办 / 记忆 / 设置 / 退出） |
| 系统托盘 | 隐藏与恢复 |

---

## 快速开始

### 环境要求

| 依赖 | 要求 |
|---|---|
| 操作系统 | Windows（主）；DPI 与 Live2D 渲染按 Windows 适配 |
| Python | **3.11 及以上** |
| 显卡 | 支持 OpenGL 3.3+ |
| 大模型 | Ollama（推荐）或 OpenAI API Key |

### 安装

```bash
git clone https://github.com/readant/ZiJin.git
cd ZiJin
pip install -r requirements.txt
```

### 准备大模型

```bash
# 方式 A：Ollama（默认，本地免费）
ollama pull qwen2.5:7b-instruct

# 方式 B：OpenAI 兼容接口
set LLM_PROVIDER=openai_api
set OPENAI_API_KEY=sk-你的密钥
```

### 启动

```bash
python main.py
```

首次启动会联网下载 ChromaDB 的嵌入模型（约 79 MB）。**下载期间对话功能正常**，仅长期记忆暂不写入；下载完成后的下一次启动自动生效。

### 验证清单

| 检查点 | 预期 |
|---|---|
| 终端日志 | `Agent就绪` → `已注册工具: [26 个]` → `子衿已上线` |
| 桌面 | 屏幕中央出现半透明悬浮窗与 Live2D 角色 |
| 双击窗口 | 出现输入框与状态栏 |
| 输入「现在几点了」 | 气泡显示真实时间（走工具调用，非模型编造） |
| 右键窗口 | 出现六项圆环菜单 |

> 模型文件缺失时应用仍可启动，仅无角色画面，对话与工具功能不受影响。

---

## 项目结构

```text
ZiJin/
├── main.py                  应用入口：配置校验 → Agent → 主窗口
├── build.py / ZiJin.spec    PyInstaller 打包
├── version.py               版本号
├── config/settings.py       唯一配置中心（环境变量 + 校验）
├── core/                    业务层（不依赖 ui/）
│   ├── agent.py             协调器：上下文组装、工具循环、情感提取
│   ├── llm.py               Ollama / OpenAI 双后端适配
│   ├── emotion.py           [情感,body:k=v] 协议解析
│   ├── tool_executor.py     工具五关流水线
│   ├── chat_history.py      聊天记录持久化
│   ├── rate_limit.py        工具频率限制
│   ├── async_executor.py    耗时任务线程池
│   ├── bus.py / log.py      事件总线 / 日志封装
│   └── memory/              短期 / 长期 / 画像 / 重要性 / 查看器
├── tools/                   26 个工具与注册表
│   ├── registry.py          @registry.register 装饰器
│   ├── safety.py            危险命令与路径校验
│   └── audit.py             data/audit.jsonl（10 MB 轮转）
├── ui/                      界面层（单向依赖 core/）
│   ├── main_window.py       悬浮窗 / 托盘 / 事件分发
│   ├── components/          Live2D、气泡、圆环菜单、状态栏
│   ├── widgets/             备忘录、待办、记忆、审计、设置面板
│   └── workers/             后台对话线程
├── models/                  Live2D 模型（Hiyori）
├── docs/                    架构与开发文档
├── tests/                   pytest 用例
└── data/                    运行时数据（已 gitignore）
```

---

## 配置

全部配置集中在 `config/settings.py`，通过环境变量覆盖：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` 或 `openai_api` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct` | 本地模型名 |
| `OPENAI_API_KEY` | 空 | 使用 `openai_api` 时必填 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | 兼容接口地址 |
| `SHORT_MEMORY_ROUNDS` | `10` | 短期记忆保留轮数 |

启动时 `validate()` 会校验非法组合并直接报错退出。

---

## 测试

```bash
# 单元测试（默认，30 项，无需外部服务）
pytest

# 集成测试（需真实 LLM 服务，默认跳过）
pytest -m integration
```

测试分两类：单元测试用 mock 隔离外部依赖；集成测试覆盖 LLM 连通性与端到端对话，因依赖真实服务而默认排除。

---

## 已知限制

- **危险操作确认未接线**：`open_application`、`close_application`、`click_position`、`search_file`、`clear_memos`、`clear_todos` 六个工具已声明 `required_confirm`，执行器会挂起等待确认，但当前界面尚未提供确认弹窗，因此这六个工具暂不可用。接线点在 `ui/main_window.py` 订阅 `tool_confirm_required` 事件。
- **嵌入模型需联网首次下载**：离线环境下长期记忆降级为「不写不检索」，短期记忆与对话不受影响。
- **设置面板尚未生效**：`ui/widgets/settings_widget.py` 写入 `data/settings.json`，但配置中心仍只读环境变量，改动需重启并以环境变量注入。
- **Live2D SDK 限制**：Python 版不支持 `HitTest` 与 `SetFocus`，视线追踪需通过 `LAppModel` 实现。
- **仅 Windows 验证**：`pycaw`、`pyautogui`、DPI 设置均为 Windows 实现。

---

## Live2D 模型声明

`models/` 下的 Hiyori 模型来自 **Live2D 官方 Cubism SDK 示例资源**，版权归 Live2D Inc. 所有，遵循 [Live2D Free Material License](https://www.live2d.com/en/terms/live2d-free-material-license-agreement/)。

本项目仅为个人学习与研究目的随仓库附带该资源，**不构成对模型素材的授权再分发**。如需商用或对外发布，请自行从 Live2D 官网获取授权，并替换 `models/` 目录内容。

本项目代码部分以 MIT 许可证发布，模型资源不在 MIT 授权范围内。

---

## 文档

| 文档 | 内容 |
|---|---|
| [DEVELOPER.md](DEVELOPER.md) | 5 分钟上手、架构图解、扩展指南、排障手册 |
| [docs/1-项目概览.md](docs/1-项目概览.md) | 定位、技术栈、入口、配置 |
| [docs/2-架构与模块详解.md](docs/2-架构与模块详解.md) | 架构风格、依赖关系、数据模型 |
| [docs/3-核心逻辑与扩展指南.md](docs/3-核心逻辑与扩展指南.md) | 核心类速查、扩展点、工具清单 |

---

## 许可

代码以 [MIT](LICENSE) 许可证发布。
