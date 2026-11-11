"""短期记忆模块"""
from datetime import datetime
from config.settings import SHORT_MEMORY_ROUNDS


class ShortMemory:
    """
    短期记忆 - 保留最近 N 轮对话
    
    存储在内存中，程序重启后清空。
    默认保留 10 轮对话 (20 条消息)。
    """

    def __init__(self, max_rounds: int = SHORT_MEMORY_ROUNDS):
        self.max_rounds = max_rounds
        self.history: list[dict] = []

    def add(self, role: str, content: str):
        """
        添加一条消息
        
        Args:
            role: "user" 或 "assistant"
            content: 消息内容
        """
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        # 超过上限，删除最早的消息
        if len(self.history) > self.max_rounds * 2:
            self.history = self.history[-self.max_rounds * 2:]

    def get_context(self) -> list[dict]:
        """获取短期记忆上下文 (不含时间戳)"""
        return [{"role": m["role"], "content": m["content"]} for m in self.history]

    def clear(self):
        """清空短期记忆"""
        self.history.clear()