"""异步工具执行器 - 长时间工具不阻塞Agent"""
import threading
from typing import Callable, Any
from core.log import get_logger

log = get_logger("async_executor")


class AsyncTask:
    def __init__(self, task_id: str, func: Callable, args: tuple, kwargs: dict):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result: Any = None
        self.error: Exception | None = None
        self.done = False
        self._event = threading.Event()

    def wait(self, timeout: float = None) -> bool:
        return self._event.wait(timeout)

    def _run(self):
        try:
            self.result = self.func(*self.args, **self.kwargs)
        except Exception as e:
            self.error = e
            log.error("异步任务 %s 失败: %s", self.task_id, e)
        finally:
            self.done = True
            self._event.set()


class AsyncExecutor:
    def __init__(self, max_workers: int = 4):
        self._tasks: dict[str, AsyncTask] = {}
        self._counter = 0
        self._lock = threading.Lock()

    def submit(self, func: Callable, *args, **kwargs) -> AsyncTask:
        with self._lock:
            self._counter += 1
            task_id = f"async_{self._counter}"

        task = AsyncTask(task_id, func, args, kwargs)
        self._tasks[task_id] = task

        t = threading.Thread(target=task._run, daemon=True)
        t.start()
        log.info("异步任务已提交: %s", task_id)
        return task

    def get_task(self, task_id: str) -> AsyncTask | None:
        return self._tasks.get(task_id)

    def cancel_all(self):
        self._tasks.clear()


async_executor = AsyncExecutor()
