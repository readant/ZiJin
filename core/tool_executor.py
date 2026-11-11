"""工具执行器 - 处理工具调用的安全验证、执行和审计"""
import json
from core.bus import bus
from core.rate_limit import rate_limiter
from tools.registry import registry
from tools.safety import validate_tool_input, needs_confirmation
from tools.audit import audit
from core.log import get_logger
from core.async_executor import async_executor

log = get_logger("tool_executor")

MAX_TOOL_ROUNDS = 3


class ToolExecutor:
    def __init__(self):
        self.pending_confirm = None
        self._async_tasks = []

    def execute_calls(self, tool_calls: list[dict], messages: list[dict]) -> tuple[list[dict], list[dict]]:
        all_calls = []
        all_results = []

        for tc in tool_calls:
            func = tc.get("function", {})
            name = func.get("name", "")
            args = func.get("arguments", "{}")

            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}

            result = self._execute_one(name, args)

            all_calls.append({"name": name, "arguments": args})
            all_results.append({"name": name, "result": result})

            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result,
            })

        return all_calls, all_results

    def _execute_one(self, name: str, args: dict, skip_confirm: bool = False) -> str:
        safety = registry.get_safety(name)

        allowed, rate_msg = rate_limiter.check(name)
        if not allowed:
            log.warning("频率限制: %s", name)
            audit.log(name=name, arguments=args, result=rate_msg,
                      safety_level=safety, blocked=True, error=rate_msg)
            return rate_msg

        # 安全校验必须早于人工确认：非法参数不应先让用户去"确认执行"
        valid, err = validate_tool_input(name, args)
        if not valid:
            log.warning("安全拒绝: %s - %s", name, err)
            audit.log(name=name, arguments=args, result=f"安全拒绝: {err}",
                      safety_level=safety, blocked=True, error=err)
            return f"安全拒绝: {err}"

        # 已确认过的调用不再重复拦截，否则确认后重入会再次挂起（死锁）
        if not skip_confirm and self._requires_confirmation(name):
            self.pending_confirm = {"name": name, "args": args}
            log.info("工具需要确认: %s %s", name, args)
            bus.emit("tool_confirm_required", name, args)
            return f"需要用户确认才能执行: {name}"

        # 异步执行耗时工具
        async_tools = {"speak", "speak_async", "open_application", "close_application", "search_file"}
        if name in async_tools:
            return self._execute_async(name, args, safety)

        try:
            bus.emit("tool_call", name, args)
            result = registry.execute(name, args)
            bus.emit("tool_result", name, result)
            audit.log(name=name, arguments=args, result=result, safety_level=safety)
            log.info("工具执行成功: %s", name)
            return result
        except Exception as e:
            error_msg = f"工具执行异常: {e}"
            log.error("工具执行失败: %s - %s", name, e)
            audit.log(name=name, arguments=args, result=error_msg,
                      safety_level=safety, error=str(e))
            return error_msg
    
    def _execute_async(self, name: str, args: dict, safety: str) -> str:
        """异步执行工具"""
        try:
            bus.emit("tool_call", name, args)
            task = async_executor.submit(registry.execute, name, **args)
            self._async_tasks.append(task)
            
            # 等待任务完成（带超时）
            if task.wait(timeout=30):
                if task.error:
                    error_msg = f"异步工具执行失败: {task.error}"
                    log.error("异步工具执行失败: %s - %s", name, task.error)
                    audit.log(name=name, arguments=args, result=error_msg,
                              safety_level=safety, error=str(task.error))
                    return error_msg
                
                result = task.result
                bus.emit("tool_result", name, result)
                audit.log(name=name, arguments=args, result=result, safety_level=safety)
                log.info("异步工具执行成功: %s", name)
                return result
            else:
                # 超时，任务仍在后台运行
                log.info("异步工具执行超时，任务继续在后台运行: %s", name)
                audit.log(name=name, arguments=args, result="任务已在后台启动", safety_level=safety)
                return "任务已在后台启动，完成后会通知"
        except Exception as e:
            error_msg = f"异步工具执行异常: {e}"
            log.error("异步工具执行失败: %s - %s", name, e)
            audit.log(name=name, arguments=args, result=error_msg,
                      safety_level=safety, error=str(e))
            return error_msg

    def _requires_confirmation(self, name: str) -> bool:
        """是否需要用户确认。

        两个来源取并集：工具的 required_confirm 声明（装饰器）与安全层的危险名单。
        此前只查安全层名单，导致 required_confirm=True 的工具被静默放行。
        """
        tool = registry.get(name)
        declared = getattr(tool, "required_confirm", False) if tool is not None else False
        # 只有明确的布尔 True 才算声明需确认，避免非 ToolDef 对象被误判
        return (isinstance(declared, bool) and declared) or needs_confirmation(name)

    def confirm_pending(self, confirmed: bool) -> str | None:
        if not self.pending_confirm:
            return None

        pending = self.pending_confirm
        self.pending_confirm = None

        if not confirmed:
            log.info("用户取消工具调用: %s", pending["name"])
            return "用户取消了操作"

        # skip_confirm=True 是关键：否则重入时会再次命中确认分支，永远执行不了
        return self._execute_one(pending["name"], pending["args"], skip_confirm=True)
    
    def cleanup_async_tasks(self):
        """清理已完成的异步任务"""
        self._async_tasks = [task for task in self._async_tasks if not task.done]
