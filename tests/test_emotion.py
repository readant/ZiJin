"""单元测试 - 情感提取模块"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.emotion import extract_emotion, build_emotion_prompt


def test_extract_happy():
    emotion, text, _ = extract_emotion("[happy] 太好了！")
    assert emotion == "happy"
    assert text == "太好了！"


def test_extract_sad():
    emotion, text, _ = extract_emotion("[sad] 好难过")
    assert emotion == "sad"
    assert text == "好难过"


def test_extract_neutral():
    emotion, text, _ = extract_emotion("没有标签的回复")
    assert emotion == "neutral"
    assert text == "没有标签的回复"


def test_extract_empty():
    emotion, text, _ = extract_emotion("")
    assert emotion == "neutral"
    assert text == ""


def test_extract_with_spaces():
    emotion, text, _ = extract_emotion("  [happy]  有空格  ")
    assert emotion == "happy"
    assert "有空格" in text


def test_build_emotion_prompt():
    prompt = build_emotion_prompt()
    assert "happy" in prompt
    assert "sad" in prompt
    assert "[情感与肢体语言输出规则]" in prompt
