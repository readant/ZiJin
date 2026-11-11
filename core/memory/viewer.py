"""记忆查看器模块"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .long_memory import LongMemory
    from .user_profile import UserProfile


class MemoryViewer:
    """
    记忆查看器 - 提供记忆查询和展示功能
    
    用于 UI 显示记忆状态和搜索历史对话。
    """

    def __init__(self, long_memory: 'LongMemory', profile: 'UserProfile'):
        self.long = long_memory
        self.profile = profile

    def get_recent(self, n: int = 10) -> list[dict]:
        """
        获取最近 n 条记忆
        
        Args:
            n: 获取的条数
            
        Returns:
            list: 记忆列表，每条包含 id, content, metadata
        """
        all_docs = self.long.collection.get()
        if not all_docs['ids']:
            return []

        memories = []
        for i in range(max(0, len(all_docs['ids']) - n), len(all_docs['ids'])):
            memories.append({
                'id': all_docs['ids'][i],
                'content': all_docs['documents'][i],
                'metadata': all_docs['metadatas'][i] if all_docs['metadatas'] else {},
            })
        return memories

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        """搜索记忆"""
        return self.long.search(query, n_results)

    def get_stats(self) -> dict:
        """
        获取详细统计
        
        Returns:
            dict: {
                "total": 总记忆数,
                "user_messages": 用户消息数,
                "assistant_messages": 助手回复数,
                "profile": 用户画像信息
            }
        """
        all_docs = self.long.collection.get()
        user_count = sum(1 for m in (all_docs['metadatas'] or []) if m.get('type') == 'user_message')
        assistant_count = sum(1 for m in (all_docs['metadatas'] or []) if m.get('type') == 'assistant_message')

        return {
            'total': self.long.collection.count(),
            'user_messages': user_count,
            'assistant_messages': assistant_count,
            'profile': {
                'name': self.profile.get_name(),
                'facts_count': len(self.profile.profile.get('facts', [])),
                'preferences_count': len(self.profile.profile.get('preferences', {})),
            }
        }

    def format_memory_list(self, memories: list[dict]) -> str:
        """
        格式化记忆列表为可读文本
        
        示例输出:
            1. [用户] 你好呀
               时间: 2024-01-01T12:00:00
            2. [子衿] [happy] 你好！
               时间: 2024-01-01T12:00:01
        """
        lines = []
        for i, mem in enumerate(memories, 1):
            msg_type = "用户" if mem['metadata'].get('type') == 'user_message' else "子衿"
            timestamp = mem['metadata'].get('timestamp', '未知时间')
            content = mem['content'][:100] + "..." if len(mem['content']) > 100 else mem['content']
            lines.append(f"{i}. [{msg_type}] {content}")
            lines.append(f"   时间: {timestamp}")
        return "\n".join(lines)

    def format_stats(self) -> str:
        """
        格式化统计信息为可读文本
        
        示例输出:
            === 记忆系统统计 ===
            总记忆数: 53
            用户消息: 28 条
            子衿回复: 25 条
            
            === 用户画像 ===
            名称: L君
            已知事实: 1 条
            用户偏好: 0 项
        """
        stats = self.get_stats()
        lines = [
            "=== 记忆系统统计 ===",
            f"总记忆数: {stats['total']}",
            f"用户消息: {stats['user_messages']} 条",
            f"子衿回复: {stats['assistant_messages']} 条",
            "",
            "=== 用户画像 ===",
            f"名称: {stats['profile']['name']}",
            f"已知事实: {stats['profile']['facts_count']} 条",
            f"用户偏好: {stats['profile']['preferences_count']} 项",
        ]
        return "\n".join(lines)