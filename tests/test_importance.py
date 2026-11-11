"""记忆重要性过滤测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直接导入importance模块，避免chromadb依赖
import re


class MessageImportance:
    """消息重要性评估器"""

    FILLER_WORDS = {
        "你好", "hello", "hi", "嗯", "哦", "好的", "ok", "okay",
        "知道了", "明白", "谢谢", "感谢", "再见", "拜拜",
        "是的", "对", "不是", "不对", "嗯嗯", "哈哈", "嘿嘿",
    }

    HIGH_VALUE_KEYWORDS = {
        "名字", "叫什么", "喜欢", "不喜欢", "讨厌", "害怕",
        "生日", "日期", "时间", "密码", "账号", "地址",
        "电话", "邮箱", "工作", "学习", "学校", "公司",
        "家人", "朋友", "爸爸", "妈妈", "哥哥", "姐姐",
        "记得", "记住", "提醒", "备忘", "重要", "关键",
        "目标", "计划", "想法", "感受", "开心", "难过",
    }

    QUESTION_PATTERNS = [
        r"什么", r"怎么", r"为什么", r"哪[里个]", r"多少",
        r"几[点个]", r"是否", r"能不能", r"可以吗", r"\?",
    ]

    @classmethod
    def score(cls, text: str, role: str = "user") -> float:
        if not text or not text.strip():
            return 0.0

        text_lower = text.lower().strip()
        score = 0.5

        length = len(text_lower)
        if length < 3:
            score -= 0.3
        elif length < 6:
            score -= 0.1
        elif length > 20:
            score += 0.1
        elif length > 50:
            score += 0.2

        filler_count = sum(1 for w in cls.FILLER_WORDS if w in text_lower)
        if filler_count > 0:
            score -= 0.1 * min(filler_count, 3)

        high_value_count = sum(1 for w in cls.HIGH_VALUE_KEYWORDS if w in text_lower)
        if high_value_count > 0:
            score += 0.1 * min(high_value_count, 3)

        is_question = any(re.search(p, text_lower) for p in cls.QUESTION_PATTERNS)
        if is_question:
            score += 0.15

        if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', text):
            score += 0.1
        elif re.search(r'\d+', text):
            score += 0.05

        if role == "assistant":
            if re.search(r'\[.*?\]', text):
                score += 0.1

        if role == "user":
            score += 0.05

        return max(0.0, min(1.0, score))

    @classmethod
    def should_store(cls, text: str, role: str = "user", threshold: float = 0.4) -> bool:
        importance = cls.score(text, role)
        return importance >= threshold

    @classmethod
    def get_importance_label(cls, score: float) -> str:
        if score >= 0.7:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"


def test_low_importance():
    tests = [
        ("你好", "user"),
        ("好的", "user"),
        ("嗯", "user"),
        ("ok", "user"),
        ("谢谢", "user"),
    ]
    for text, role in tests:
        score = MessageImportance.score(text, role)
        should_store = MessageImportance.should_store(text, role)
        print(f"  [{role}] '{text}' → {score:.2f} ({'存储' if should_store else '跳过'})")


def test_high_importance():
    tests = [
        ("我叫张三，你记住", "user"),
        ("我喜欢吃火锅，不喜欢吃海鲜", "user"),
        ("明天下午3点有个会议", "user"),
        ("我的生日是1995年5月20日", "user"),
        ("记得提醒我买菜", "user"),
        ("你叫什么名字？", "user"),
    ]
    for text, role in tests:
        score = MessageImportance.score(text, role)
        should_store = MessageImportance.should_store(text, role)
        print(f"  [{role}] '{text[:25]}' → {score:.2f} ({'存储' if should_store else '跳过'})")


if __name__ == "__main__":
    print("=== 记忆重要性过滤测试 ===")
    print("\n1. 低重要性消息 (应跳过):")
    test_low_importance()
    
    print("\n2. 高重要性消息 (应存储):")
    test_high_importance()
    
    print("\n✅ 测试完成!")