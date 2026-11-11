"""统一记忆管理器模块"""
from .short_memory import ShortMemory
from .long_memory import LongMemory
from .user_profile import UserProfile
from .viewer import MemoryViewer
from .importance import importance
from core.log import get_logger

log = get_logger("memory")


class MemoryManager:
    """
    统一记忆管理器 - 协调三层记忆
    
    使用方法：
        manager = MemoryManager()
        
        # 添加对话
        manager.add_conversation("user", "你好")
        manager.add_conversation("assistant", "[happy] 你好呀！")
        
        # 构建上下文
        context = manager.build_context("最近怎么样？")
        
        # 查看统计
        stats = manager.get_stats()
    """

    def __init__(self):
        self.short = ShortMemory()      # 短期记忆
        self.long = LongMemory()        # 长期记忆
        self.profile = UserProfile()    # 用户画像
        self.viewer = MemoryViewer(self.long, self.profile)  # 记忆查看器

    def add_conversation(self, role: str, content: str, skip_dedup: bool = False):
        """
        添加一条对话到记忆
        
        短期记忆：所有消息都存储
        长期记忆：只存储重要消息（过滤低价值内容）
        
        Args:
            role: "user" 或 "assistant"
            content: 消息内容
            skip_dedup: 是否跳过去重检查
        """
        self.short.add(role, content)
        
        # 计算重要性
        score = importance.score(content, role)
        label = importance.get_importance_label(score)
        
        # 长期记忆：只存储中等及以上重要性的内容
        if importance.should_store(content, role):
            metadata = {
                "type": f"{role}_message",
                "importance": label,
                "importance_score": round(score, 2),
            }
            doc_id = self.long.add(content, metadata, skip_dedup=skip_dedup)
            if doc_id:
                log.debug("存储长期记忆 [%s]: %s", label, content[:30])
            else:
                log.debug("跳过重复记忆: %s", content[:30])
        else:
            log.debug("跳过低价值消息: %s", content[:30])

    def build_context(self, current_query: str = None) -> list[dict]:
        """
        构建 LLM 上下文
        
        组合：
        1. 用户画像 (姓名、偏好、事实)
        2. 相关记忆 (基于当前查询的向量检索)
        3. 短期记忆 (最近对话)
        
        Args:
            current_query: 当前用户查询 (用于检索相关记忆)
            
        Returns:
            list: 消息列表，可直接用于 LLM
        """
        messages = []

        # 1. 用户画像
        profile_section = self.profile.to_prompt_section()
        if profile_section:
            messages.append({
                "role": "system",
                "content": f"[用户信息]\n{profile_section}",
            })

        # 2. 相关记忆 (向量检索)
        if current_query:
            memories = self.long.search(current_query, n_results=3)
            if memories:
                mem_text = "\n".join(f"- {m['content'][:100]}" for m in memories)
                messages.append({
                    "role": "system",
                    "content": f"[相关记忆]\n{mem_text}",
                })

        # 3. 短期记忆
        messages.extend(self.short.get_context())
        
        return messages

    def clear_short(self):
        """清空短期记忆"""
        self.short.clear()

    def clear_long(self):
        """清空长期记忆"""
        self.long.clear()

    def clear_all(self):
        """清空所有记忆"""
        self.short.clear()
        self.long.clear()

    def get_stats(self) -> dict:
        """获取记忆统计"""
        return {
            "short_memory_size": len(self.short.history),
            "long_memory": self.long.get_stats(),
        }

    def get_viewer(self) -> MemoryViewer:
        """获取记忆查看器 (用于 UI 显示)"""
        return self.viewer