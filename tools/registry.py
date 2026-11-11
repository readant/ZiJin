"""
工具注册表 - 装饰器式注册，支持 LLM function calling

原理：
    使用装饰器自动注册工具函数，生成 LLM 可理解的工具定义。
    当 LLM 返回工具调用时，通过注册表执行对应函数。

使用方法：
    from tools.registry import registry
    
    @registry.register(
        name="get_time",
        description="获取当前时间",
        parameters={}
    )
    def get_time() -> str:
        return datetime.now().strftime("%H:%M:%S")
    
    # 执行工具
    result = registry.execute("get_time", {})
"""
from typing import Callable, Any
from dataclasses import dataclass, field


@dataclass
class ToolDef:
    """
    工具定义
    
    Attributes:
        name: 工具名称 (LLM 调用时使用的名称)
        description: 工具描述 (LLM 根据此判断何时使用)
        func: 工具函数
        parameters: 参数定义 (JSON Schema 格式)
        safety_level: 安全级别 (safe/moderate/dangerous)
        required_confirm: 是否需要用户确认
    """
    name: str
    description: str
    func: Callable
    parameters: dict
    safety_level: str = "safe"  # safe | moderate | dangerous
    required_confirm: bool = False


class ToolRegistry:
    """
    工具注册表
    
    功能：
    - register(): 装饰器注册工具
    - execute(): 执行工具
    - definitions_for_llm(): 生成 LLM 格式的工具定义
    """

    def __init__(self):
        # 存储所有注册的工具: {"tool_name": ToolDef}
        self._tools: dict[str, ToolDef] = {}

    def register(self, name: str = None, description: str = "",
                 parameters: dict = None, safety_level: str = "safe",
                 required_confirm: bool = False):
        """
        装饰器注册工具
        
        Args:
            name: 工具名称 (默认使用函数名)
            description: 工具描述
            parameters: 参数定义 (JSON Schema)
            safety_level: 安全级别
            required_confirm: 是否需要确认
            
        Example:
            @registry.register(
                name="add_memo",
                description="添加备忘录",
                parameters={
                    "content": {"type": "string", "description": "备忘内容"}
                }
            )
            def add_memo(content: str) -> str:
                ...
        """
        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_def = ToolDef(
                name=tool_name,
                description=description or func.__doc__ or "",
                func=func,
                parameters=parameters or {},
                safety_level=safety_level,
                required_confirm=required_confirm,
            )
            self._tools[tool_name] = tool_def
            return func
        return decorator

    def get(self, name: str) -> ToolDef | None:
        """获取工具定义"""
        return self._tools.get(name)

    def execute(self, name: str, arguments: dict) -> str:
        """
        执行工具
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            str: 执行结果
        """
        tool = self._tools.get(name)
        if not tool:
            return f"未知工具: {name}"
        # 工具自身的异常不再在此吞掉：交给 ToolExecutor 统一捕获并写入 audit.error，
        # 否则审计日志永远拿不到真实错误原因。
        return tool.func(**arguments)

    def definitions_for_llm(self) -> list[dict]:
        """
        生成 LLM function calling 格式的工具定义
        
        输出格式:
        [
            {
                "type": "function",
                "function": {
                    "name": "get_time",
                    "description": "获取当前时间",
                    "parameters": {}
                }
            }
        ]
        """
        defs = []
        for tool in self._tools.values():
            defs.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })
        return defs

    def list_tools(self) -> list[str]:
        """列出所有已注册的工具名称"""
        return list(self._tools.keys())

    def get_safety(self, name: str) -> str:
        """获取工具的安全级别"""
        tool = self._tools.get(name)
        return tool.safety_level if tool else "unknown"


# 全局工具注册表实例
registry = ToolRegistry()
