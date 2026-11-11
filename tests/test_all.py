"""集成测试 - 验证所有模块功能

需要真实 LLM 服务（Ollama 或 OpenAI）与联网下载嵌入模型，
默认不在 `pytest` 中执行；显式运行：pytest -m integration
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

pytestmark = pytest.mark.integration

from core.llm import LLMClient
from core.memory import MemoryManager
from core.emotion import extract_emotion
from tools.registry import registry


def test_llm():
    print("=" * 50)
    print("测试1: LLM连接")
    client = LLMClient()
    messages = [
        {"role": "system", "content": "你是一个助手。"},
        {"role": "user", "content": "你好！"},
    ]
    resp = client.chat(messages)
    print(f"回复: {resp['content']}")
    assert resp["content"], "LLM返回为空"
    print("[OK] LLM连接测试通过")
    return True


def test_emotion():
    print("=" * 50)
    print("测试2: 情感提取")
    cases = [
        ("[happy] 太好了！", "happy", "太好了！"),
        ("[thinking] 让我想想", "thinking", "让我想想"),
        ("没有标签", "neutral", "没有标签"),
    ]
    for text, expect_emotion, expect_text in cases:
        emotion, clean, _ = extract_emotion(text)
        assert emotion == expect_emotion, f"期望 {expect_emotion}，得到 {emotion}"
        assert expect_text in clean, f"期望包含 {expect_text}，得到 {clean}"
        print(f"  [OK] '{text}' -> emotion={emotion}, clean='{clean}'")
    print("[OK] 情感提取测试通过")
    return True


def test_memory():
    print("=" * 50)
    print("测试3: 记忆系统")
    mm = MemoryManager()

    mm.add_conversation("user", "今天天气怎么样？")
    mm.add_conversation("assistant", "[happy] 今天天气很好！")
    ctx = mm.short.get_context()
    assert len(ctx) == 2, f"短期记忆应有2条，实际 {len(ctx)}"
    print(f"  [OK] 短期记忆: {len(ctx)}条")

    mm.profile.set_name("张三")
    mm.profile.add_fact("喜欢编程")
    prompt = mm.profile.to_prompt_section()
    assert "张三" in prompt
    print(f"  [OK] 用户画像: {prompt[:50]}...")

    stats = mm.get_stats()
    print(f"  [OK] 记忆状态: {stats}")

    print("[OK] 记忆系统测试通过")
    return True


def test_tools():
    print("=" * 50)
    print("测试4: 工具系统")
    tool_list = registry.list_tools()
    print(f"  工具数量: {len(tool_list)}")
    for name in tool_list:
        tool = registry.get(name)
        print(f"  - {name}: {tool.description[:40]}")

    result = registry.execute("get_system_info", {})
    print(f"  [OK] 系统信息: {result[:80]}...")

    print("[OK] 工具系统测试通过")
    return True


def test_agent_integration():
    print("=" * 50)
    print("测试5: Agent集成")
    from core.agent import Agent

    agent = Agent()
    print(f"  Agent模型: {agent.llm.model}")

    resp = agent.chat("你好！")
    try:
        print(f"  回复情感: {resp['emotion']}")
        print(f"  回复内容: {resp['text'][:50]}")
    except UnicodeEncodeError:
        print(f"  回复情感: {resp['emotion']}")
        print(f"  回复内容: (unicode)")
    assert resp["emotion"] in ["happy", "neutral", "excited", "thinking", "shy"]
    assert resp["text"]

    resp2 = agent.chat("查看系统信息")
    try:
        print(f"  工具调用: {resp2.get('tool_calls')}")
        print(f"  回复内容: {resp2['text'][:50]}")
    except UnicodeEncodeError:
        print(f"  工具调用: (has tool_calls: {resp2.get('tool_calls') is not None})")
        print(f"  回复内容: (unicode)")

    stats = agent.get_memory_stats()
    print(f"  记忆状态: {stats}")

    print("[OK] Agent集成测试通过")
    return True


if __name__ == "__main__":
    results = []
    tests = [
        ("LLM", test_llm),
        ("情感", test_emotion),
        ("记忆", test_memory),
        ("工具", test_tools),
        ("Agent集成", test_agent_integration),
    ]

    for name, test_func in tests:
        try:
            ok = test_func()
            results.append((name, ok))
        except Exception as e:
            print(f"[FAIL] {name}测试失败: {e}")
            results.append((name, False))

    print("\n" + "=" * 50)
    print("测试结果汇总:")
    for name, ok in results:
        status = "[PASS]" if ok else "[FAIL]"
        print(f"  {name}: {status}")

    all_pass = all(ok for _, ok in results)
    print(f"\n{'全部通过！' if all_pass else '存在失败项'}")
    sys.exit(0 if all_pass else 1)
