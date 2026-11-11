"""LLM工作线程模块 - 使用 threading 避免 PyQt 线程问题"""
import threading
import queue
from core.log import get_logger

log = get_logger("llm_worker")


class LLMWorker:
    """LLM工作线程 - 使用 threading.Queue 安全通信"""

    def __init__(self, agent, text, use_stream=False):
        self.agent = agent
        self.text = text
        self.use_stream = use_stream
        self.chunk_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self._thread = None

    def start(self):
        """启动工作线程"""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        """在线程中执行 LLM 调用"""
        try:
            if self.use_stream:
                for chunk in self.agent.chat_stream(self.text):
                    self.chunk_queue.put(("chunk", chunk))
                    if chunk.get("type") == "done":
                        break
                self.result_queue.put(("result", {"emotion": "neutral", "text": ""}))
            else:
                result = self.agent.chat(self.text)
                self.result_queue.put(("result", result))
        except Exception as e:
            log.error("LLM 调用错误: %s", e)
            self.result_queue.put(("result", {"emotion": "sad", "text": f"出错了: {e}"}))

    def is_running(self):
        """检查线程是否在运行"""
        return self._thread is not None and self._thread.is_alive()

    def get_chunk(self):
        """获取一个 chunk（非阻塞）"""
        try:
            return self.chunk_queue.get_nowait()
        except queue.Empty:
            return None

    def get_result(self):
        """获取最终结果（非阻塞）"""
        try:
            return self.result_queue.get_nowait()
        except queue.Empty:
            return None