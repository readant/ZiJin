# 贡献指南

感谢你对子衿项目的关注！本文档将帮助你快速上手贡献代码。

## 开发环境搭建

### 1. 克隆项目
```bash
git clone https://github.com/your-username/ZiJin.git
cd ZiJin
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境
复制 `config/settings.example.py` 为 `config/settings.py`，并配置：
- LLM 提供商（Ollama 或 OpenAI API）
- 模型路径
- 其他配置项

### 4. 运行项目
```bash
python main.py
```

## 项目结构

```
ZiJin/
├── config/          # 配置文件
├── core/            # 核心模块
│   ├── agent.py     # Agent 协调器
│   ├── llm.py       # LLM 调用
│   ├── memory/      # 记忆系统
│   ├── emotion.py   # 情感分析
│   └── bus.py       # 事件总线
├── tools/           # 桌面工具
├── ui/              # 界面
│   ├── components/  # 可复用组件
│   ├── widgets/     # 功能小部件
│   └── workers/     # 工作线程
├── models/          # Live2D 模型
├── data/            # 数据存储 (gitignore)
├── tests/           # 测试
└── docs/            # 文档
```

## 开发流程

### 1. 创建分支
```bash
git checkout -b feature/your-feature-name
```

### 2. 编写代码
- 遵循 PEP 8 代码规范
- 为新功能添加文档字符串
- 保持模块职责单一

### 3. 添加测试
```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_emotion.py
```

### 4. 提交代码
```bash
git add .
git commit -m "feat: 添加新功能描述"
git push origin feature/your-feature-name
```

### 5. 创建 Pull Request
在 GitHub 上创建 PR，详细描述你的改动。

## 代码规范

### Python 代码
- 使用 4 空格缩进
- 行长度不超过 88 字符
- 使用 type hints
- 为公共函数添加 docstring

### 提交信息
使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：
- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具相关

## 添加新工具

1. 在 `tools/` 目录下创建新文件
2. 使用装饰器注册工具：
```python
from tools.registry import registry

@registry.register(
    name="my_tool",
    description="我的工具描述",
    parameters={
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "参数描述"}
        },
        "required": ["param"]
    },
    safety_level="safe"  # safe/moderate/dangerous
)
def my_tool(param: str) -> str:
    """工具实现"""
    return f"结果: {param}"
```

3. 在 `tools/__init__.py` 中导入新工具
4. 添加测试

## 添加新 UI 组件

1. 在 `ui/components/` 目录下创建新组件
2. 继承 `BaseFloatingWidget` 或 `QWidget`
3. 实现必要的接口
4. 在 `main_window.py` 中集成

## 测试规范

### 单元测试
- 测试文件命名：`test_*.py`
- 测试类命名：`Test*`
- 测试方法命名：`test_*`

### 集成测试
- 测试完整工作流
- 使用 mock 隔离外部依赖

### 运行测试
```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_emotion.py -v

# 生成覆盖率报告
python -m pytest tests/ --cov=core --cov=tools
```

## 文档贡献

### 代码文档
- 为公共 API 添加 docstring
- 使用 Google 风格的 docstring

### 用户文档
- 在 `docs/` 目录下添加 markdown 文档
- 更新 README.md

## 问题报告

### Bug 报告
请包含：
1. 问题描述
2. 复现步骤
3. 期望行为
4. 实际行为
5. 环境信息（Python 版本、操作系统等）

### 功能请求
请包含：
1. 功能描述
2. 使用场景
3. 期望实现方式

## 行为准则

- 尊重所有贡献者
- 接受建设性批评
- 专注于对社区最有利的事情
- 对其他社区成员表示同理心

## 许可证

贡献即表示你同意你的代码在 MIT 许可证下发布。