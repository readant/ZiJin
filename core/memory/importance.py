"""记忆重要性过滤模块"""
import re
from core.log import get_logger

log = get_logger("memory_importance")


class MessageImportance:
    """消息重要性评估器"""

    # 低价值关键词（出现则降低重要性）
    FILLER_WORDS = {
        "你好", "hello", "hi", "嗯", "哦", "好的", "ok", "okay",
        "知道了", "明白", "谢谢", "感谢", "再见", "拜拜",
        "是的", "对", "不是", "不对", "嗯嗯", "哈哈", "嘿嘿",
    }

    # 高价值关键词（出现则提高重要性）
    HIGH_VALUE_KEYWORDS = {
        "名字", "叫什么", "喜欢", "不喜欢", "讨厌", "害怕",
        "生日", "日期", "时间", "密码", "账号", "地址",
        "电话", "邮箱", "工作", "学习", "学校", "公司",
        "家人", "朋友", "爸爸", "妈妈", "哥哥", "姐姐",
        "记得", "记住", "提醒", "备忘", "重要", "关键",
        "目标", "计划", "想法", "感受", "开心", "难过",
    }

    # 问题模式
    QUESTION_PATTERNS = [
        r"什么", r"怎么", r"为什么", r"哪[里个]", r"多少",
        r"几[点个]", r"是否", r"能不能", r"可以吗", r"\?",
    ]

    @classmethod
    def score(cls, text: str, role: str = "user") -> float:
        """
        计算消息重要性分数 (0.0 ~ 1.0)
        
        Args:
            text: 消息内容
            role: 角色 (user/assistant)
            
        Returns:
            float: 重要性分数
        """
        if not text or not text.strip():
            return 0.0

        text_lower = text.lower().strip()
        score = 0.5  # 基础分

        # 1. 长度因素 (0.0 ~ 0.2)
        length = len(text_lower)
        if length < 3:
            score -= 0.3
        elif length < 6:
            score -= 0.1
        elif length > 50:
            score += 0.2
        elif length > 20:
            score += 0.1

        # 2. 低价值词检测 (-0.3 ~ 0)
        filler_count = sum(1 for w in cls.FILLER_WORDS if w in text_lower)
        if filler_count > 0:
            score -= 0.1 * min(filler_count, 3)

        # 3. 高价值词检测 (0 ~ 0.3)
        high_value_count = sum(1 for w in cls.HIGH_VALUE_KEYWORDS if w in text_lower)
        if high_value_count > 0:
            score += 0.1 * min(high_value_count, 3)

        # 4. 问题检测 (0 ~ 0.15)
        is_question = any(re.search(p, text_lower) for p in cls.QUESTION_PATTERNS)
        if is_question:
            score += 0.15

        # 5. 数字/日期检测 (0 ~ 0.1)
        if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', text):  # 日期
            score += 0.1
        elif re.search(r'\d+', text):  # 包含数字
            score += 0.05

        # 6. 情感标签检测 (assistant专用)
        if role == "assistant":
            if re.search(r'\[.*?\]', text):  # 有情感标签
                score += 0.1

        # 7. 用户消息比助手消息更重要
        if role == "user":
            score += 0.05

        # 限制范围
        return max(0.0, min(1.0, score))

    @classmethod
    def should_store(cls, text: str, role: str = "user", threshold: float = 0.4) -> bool:
        """
        判断是否应该存储到长期记忆
        
        Args:
            text: 消息内容
            role: 角色
            threshold: 重要性阈值 (默认0.4)
            
        Returns:
            bool: 是否应该存储
        """
        score = cls.score(text, role)
        return score >= threshold

    @classmethod
    def get_importance_label(cls, score: float) -> str:
        """获取重要性标签"""
        if score >= 0.7:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"


# 全局实例
importance = MessageImportance()