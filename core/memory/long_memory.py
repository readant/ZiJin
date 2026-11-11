"""长期记忆模块 - 性能优化版"""
import json
import os
import time
import uuid
import threading
from datetime import datetime
from typing import Optional
import chromadb
from config.settings import CHROMA_DB_PATH, CHROMA_COLLECTION
from core.log import get_logger

log = get_logger("long_memory")


class LongMemory:
    """
    长期记忆 - 基于 ChromaDB 的向量检索 RAG (性能优化版)
    
    优化点:
    1. UUID替代时间戳ID，避免冲突
    2. 批量操作支持
    3. 智能缓存管理
    4. 去重机制
    5. 线程安全
    """

    def __init__(self, dedup_threshold: float = 0.95):
        """
        初始化 ChromaDB 客户端
        
        Args:
            dedup_threshold: 去重相似度阈值 (0-1)，超过此值视为重复
        """
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self._dedup_threshold = dedup_threshold
        self._lock = threading.Lock()
        
        try:
            self.collection = self.client.get_collection(CHROMA_COLLECTION)
        except Exception:
            self.collection = self.client.create_collection(
                name=CHROMA_COLLECTION,
                metadata={"hnsw:space": "cosine"}
            )
        
        self._count_cache: Optional[int] = None
        self._cache_time = 0.0
        self._cache_ttl = 5.0  # 缓存有效期5秒

        # === 嵌入模型就绪状态 ===
        # chromadb 的默认嵌入函数首次使用会下载 all-MiniLM-L6-v2（约 79MB）。
        # 弱网/离线时该下载会无限挂起，且 chromadb 不抛异常、不超时。
        # 因此这里改为「后台预热 + 未就绪降级」，绝不让下载阻塞对话路径。
        self._embed_ready = False
        self._embed_error = ""
        self._start_warmup()

    def _start_warmup(self):
        """后台线程预热嵌入模型，不阻塞构造与首次对话"""
        t = threading.Thread(target=self._warmup_embedding,
                            name="long-memory-warmup", daemon=True)
        t.start()
        # 预热超时观测：线程无法被强制中断，但状态要对使用者可见
        timer = threading.Timer(30.0, self._mark_warmup_timeout)
        timer.daemon = True
        timer.start()

    def _mark_warmup_timeout(self):
        """预热超过 30s 仍未就绪，标记原因供 stats/排障查看"""
        if not self._embed_ready and not self._embed_error:
            self._embed_error = "预热超时（可能仍在下载嵌入模型）"
            log.warning("长期记忆嵌入模型预热超过 30s，当前按降级模式运行")

    def _warmup_embedding(self):
        """探测嵌入模型可用性；失败则标记降级，不做任何阻塞重试"""
        try:
            # 优先直接调用嵌入函数：即使集合为空也能真实触发模型加载
            ef = getattr(self.collection, "_embedding_function", None)
            if ef is not None:
                ef(["warmup"])
            else:
                self.collection.query(query_texts=["warmup"], n_results=1)
            self._embed_ready = True
            self._embed_error = ""
            log.info("长期记忆嵌入模型已就绪")
        except Exception as e:
            self._embed_error = str(e) or e.__class__.__name__
            log.warning(
                "长期记忆嵌入模型不可用，已降级为「不写不检索」: %s。"
                "该模型需联网下载（约 79MB），联网启动一次即可完成缓存。",
                self._embed_error,
            )

    def _embed_available(self) -> bool:
        """嵌入模型是否可用于向量操作"""
        return self._embed_ready

    def _get_count(self) -> int:
        """获取文档数量（带缓存）"""
        now = time.time()
        if self._count_cache is None or (now - self._cache_time) > self._cache_ttl:
            self._count_cache = self.collection.count()
            self._cache_time = now
        return self._count_cache

    def _invalidate_cache(self):
        """使缓存失效"""
        self._count_cache = None
        self._cache_time = 0.0

    def _generate_id(self) -> str:
        """生成唯一ID (UUID + 时间戳)"""
        return f"doc_{uuid.uuid4().hex[:12]}_{int(time.time() * 1000)}"

    def _check_duplicate(self, text: str) -> bool:
        """检查是否重复内容"""
        if not self._embed_available():
            return False
        count = self._get_count()
        if count == 0:
            return False
        
        try:
            results = self.collection.query(
                query_texts=[text],
                n_results=1,
            )
            if results["distances"] and results["distances"][0]:
                distance = results["distances"][0][0]
                # 余弦距离越小越相似，1 - distance = 相似度
                similarity = 1 - distance
                return similarity >= self._dedup_threshold
        except Exception:
            pass
        return False

    def add(self, text: str, metadata: dict = None, skip_dedup: bool = False) -> str:
        """
        添加一条记忆
        
        Args:
            text: 记忆内容
            metadata: 元数据
            skip_dedup: 是否跳过去重检查
            
        Returns:
            str: 文档ID
        """
        if not text or not text.strip():
            return ""

        if not self._embed_available():
            log.debug("嵌入模型未就绪，跳过长期记忆写入: %s", text[:30])
            return ""

        # 去重检查
        if not skip_dedup and self._check_duplicate(text):
            log.debug("跳过重复记忆: %s", text[:30])
            return ""
        
        if metadata is None:
            metadata = {}
        metadata["timestamp"] = datetime.now().isoformat()
        metadata["text_length"] = len(text)
        
        doc_id = self._generate_id()
        
        with self._lock:
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[doc_id],
            )
            self._invalidate_cache()
        
        return doc_id

    def add_batch(self, items: list[dict]) -> int:
        """
        批量添加记忆
        
        Args:
            items: [{"text": str, "metadata": dict}, ...]
            
        Returns:
            int: 成功添加的数量
        """
        if not items:
            return 0

        if not self._embed_available():
            log.debug("嵌入模型未就绪，跳过批量写入（%d 条）", len(items))
            return 0

        documents = []
        metadatas = []
        ids = []
        
        for item in items:
            text = item.get("text", "")
            if not text or not text.strip():
                continue
            
            if not self._check_duplicate(text):
                metadata = item.get("metadata", {})
                metadata["timestamp"] = datetime.now().isoformat()
                metadata["text_length"] = len(text)
                
                documents.append(text)
                metadatas.append(metadata)
                ids.append(self._generate_id())
        
        if not documents:
            return 0
        
        with self._lock:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            self._invalidate_cache()
        
        log.info("批量添加 %d 条记忆", len(documents))
        return len(documents)

    def search(self, query: str, n_results: int = 5, 
               where: dict = None, min_score: float = 0.0) -> list[dict]:
        """
        搜索相关记忆 (向量检索)
        
        Args:
            query: 查询文本
            n_results: 返回的结果数量
            where: 过滤条件 (ChromaDB where语法)
            min_score: 最小相似度阈值 (0-1)
            
        Returns:
            list: 相关记忆列表
        """
        count = self._get_count()
        if count == 0:
            return []

        if not self._embed_available():
            log.debug("嵌入模型未就绪，跳过向量检索: %s", query[:30])
            return []

        try:
            query_params = {
                "query_texts": [query],
                "n_results": min(n_results, count),
            }
            if where:
                query_params["where"] = where
            
            results = self.collection.query(**query_params)
            
            memories = []
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                similarity = 1 - distance  # 转换为相似度
                
                if similarity < min_score:
                    continue
                
                memories.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": distance,
                    "similarity": round(similarity, 3),
                })
            
            return memories
            
        except Exception as e:
            log.error("记忆搜索失败: %s", e)
            return []

    def delete(self, ids: list[str]) -> int:
        """
        批量删除记忆
        
        Args:
            ids: 文档ID列表
            
        Returns:
            int: 删除数量
        """
        if not ids:
            return 0
        
        with self._lock:
            self.collection.delete(ids=ids)
            self._invalidate_cache()
        
        return len(ids)

    def delete_by_type(self, msg_type: str) -> int:
        """按类型删除记忆"""
        try:
            results = self.collection.get(
                where={"type": msg_type}
            )
            if results["ids"]:
                return self.delete(results["ids"])
        except Exception:
            # ChromaDB where条件失败时回退到遍历
            all_docs = self.collection.get()
            ids_to_delete = []
            for i, meta in enumerate(all_docs['metadatas'] or []):
                if meta.get('type') == msg_type:
                    ids_to_delete.append(all_docs['ids'][i])
            if ids_to_delete:
                return self.delete(ids_to_delete)
        return 0

    def get_stats(self) -> dict:
        """获取统计信息"""
        count = self._get_count()
        return {
            "total_documents": count,
            "cache_valid": (time.time() - self._cache_time) < self._cache_ttl,
            "embedding_ready": self._embed_ready,
            "embedding_error": self._embed_error,
        }

    def get_all(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """获取所有记忆 (分页)"""
        results = self.collection.get(limit=limit, offset=offset)
        memories = []
        for i, doc_id in enumerate(results['ids']):
            memories.append({
                'id': doc_id,
                'content': results['documents'][i],
                'metadata': results['metadatas'][i] if results['metadatas'] else {},
            })
        return memories

    def clear(self):
        """清空所有长期记忆"""
        with self._lock:
            self.client.delete_collection(CHROMA_COLLECTION)
            self.collection = self.client.create_collection(
                name=CHROMA_COLLECTION,
                metadata={"hnsw:space": "cosine"}
            )
            self._invalidate_cache()
        log.info("长期记忆已清空")

    def export_to_json(self, filepath: str):
        """导出记忆到 JSON 文件"""
        all_docs = self.collection.get()
        export_data = []
        for i, doc_id in enumerate(all_docs['ids']):
            export_data.append({
                'id': doc_id,
                'content': all_docs['documents'][i],
                'metadata': all_docs['metadatas'][i] if all_docs['metadatas'] else {},
            })
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        log.info("导出 %d 条记忆到 %s", len(export_data), filepath)

    def import_from_json(self, filepath: str) -> int:
        """从 JSON 文件导入记忆"""
        with open(filepath, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        items = [{"text": item['content'], "metadata": item.get('metadata', {})} 
                 for item in import_data]
        count = self.add_batch(items)
        log.info("从 %s 导入 %d 条记忆", filepath, count)
        return count