"""聊天记录持久化模块"""
import json
import os
from datetime import datetime
from typing import List, Dict
from config.settings import DATA_DIR
from core.log import get_logger

log = get_logger("chat_history")


class ChatHistory:
    """聊天记录管理器"""

    def __init__(self, max_history: int = 100):
        """
        初始化聊天记录管理器
        
        Args:
            max_history: 最大保存的历史消息数
        """
        self.max_history = max_history
        self._history_path = os.path.join(DATA_DIR, "chat_history.json")
        self._history: List[Dict] = []
        self._load()

    def _load(self):
        """从文件加载聊天记录"""
        if os.path.exists(self._history_path):
            try:
                with open(self._history_path, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
                log.info("加载聊天记录: %d 条", len(self._history))
            except Exception as e:
                log.error("加载聊天记录失败: %s", e)
                self._history = []
        else:
            self._history = []

    def _save(self):
        """保存聊天记录到文件"""
        try:
            os.makedirs(os.path.dirname(self._history_path), exist_ok=True)
            # 只保存最近的记录
            history_to_save = self._history[-self.max_history:]
            with open(self._history_path, "w", encoding="utf-8") as f:
                json.dump(history_to_save, f, ensure_ascii=False, indent=2)
            log.debug("保存聊天记录: %d 条", len(history_to_save))
        except Exception as e:
            log.error("保存聊天记录失败: %s", e)

    def add_message(self, role: str, content: str, emotion: str = None, metadata: Dict = None):
        """
        添加一条消息
        
        Args:
            role: "user" 或 "assistant"
            content: 消息内容
            emotion: 情感标签（仅assistant）
            metadata: 额外元数据
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        
        if emotion:
            message["emotion"] = emotion
        
        if metadata:
            message["metadata"] = metadata
        
        self._history.append(message)
        
        # 超过上限，删除最早的消息
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]
        
        # 异步保存（简单实现）
        self._save()

    def get_history(self, limit: int = None) -> List[Dict]:
        """
        获取聊天记录
        
        Args:
            limit: 返回的最大消息数，None返回全部
            
        Returns:
            消息列表
        """
        if limit:
            return self._history[-limit:]
        return self._history.copy()

    def get_recent(self, n: int = 10) -> List[Dict]:
        """获取最近n条消息"""
        return self._history[-n:]

    def search(self, keyword: str) -> List[Dict]:
        """
        搜索聊天记录
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的消息列表
        """
        results = []
        keyword_lower = keyword.lower()
        for msg in self._history:
            if keyword_lower in msg.get("content", "").lower():
                results.append(msg)
        return results

    def get_stats(self) -> Dict:
        """获取统计信息"""
        user_count = sum(1 for m in self._history if m.get("role") == "user")
        assistant_count = sum(1 for m in self._history if m.get("role") == "assistant")
        
        return {
            "total": len(self._history),
            "user_messages": user_count,
            "assistant_messages": assistant_count,
        }

    def clear(self):
        """清空聊天记录"""
        self._history = []
        self._save()
        log.info("聊天记录已清空")

    def export_to_json(self, filepath: str):
        """导出聊天记录到JSON文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._history, f, ensure_ascii=False, indent=2)
        log.info("导出聊天记录到: %s", filepath)

    def import_from_json(self, filepath: str):
        """从JSON文件导入聊天记录"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                imported = json.load(f)
            if isinstance(imported, list):
                self._history.extend(imported)
                # 去重（按时间戳）
                seen = set()
                unique_history = []
                for msg in self._history:
                    ts = msg.get("timestamp")
                    if ts not in seen:
                        seen.add(ts)
                        unique_history.append(msg)
                self._history = sorted(unique_history, key=lambda x: x.get("timestamp", ""))
                # 限制数量
                if len(self._history) > self.max_history:
                    self._history = self._history[-self.max_history:]
                self._save()
                log.info("导入聊天记录: %d 条", len(imported))
        except Exception as e:
            log.error("导入聊天记录失败: %s", e)


# 全局聊天记录实例
chat_history = ChatHistory()