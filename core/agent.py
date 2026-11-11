"""
核心 Agent 模块 - 精简协调器

职责：
    - 接收用户输入
    - 构建上下文 (记忆 + 用户画像)
    - 调用 LLM 获取回复
    - 协调工具执行
    - 提取情感标签
    - 存储对话到记忆
"""

from core.bus import bus
from core.llm import LLMClient
from core.memory import MemoryManager
from core.emotion import extract_emotion, extract_emotion_simple, build_emotion_prompt
from core.tool_executor import ToolExecutor, MAX_TOOL_ROUNDS
from core.chat_history import chat_history
from tools.registry import registry
from config.settings import SYSTEM_PROMPT, TOOLS_ENABLED
from core.log import get_logger
import re

log = get_logger("agent")

FALLBACK_RULES = [
    {
        "patterns": [r"几点", r"什么时间", r"现在时间", r"几点了", r"几点钟"],
        "tool": "get_current_time",
        "args": {},
    },
    {
        "patterns": [r"今天.*日期", r"什么日期", r"几月几号", r"几号"],
        "tool": "get_current_date",
        "args": {},
    },
    {
        "patterns": [r"音量.*(多少|多大|查看|看看|查询)"],
        "tool": "get_volume",
        "args": {},
    },
    {
        "patterns": [
            r"(?:调|设|改|将|把)[^\d]{0,10}音量[^\d]{0,10}(\d+)",
            r"音量[^\d]*(\d+)",
        ],
        "tool": "set_volume",
        "extract_args": lambda m: {"level": int(m.group(1))},
    },
    {
        "patterns": [r"静音", r"关闭声音", r"mute"],
        "tool": "toggle_mute",
        "args": {},
    },
]


class Agent:
    """
    桌面助手 Agent - 协调 LLM、记忆、工具

    返回格式：
        {
            "emotion": "happy",
            "text": "你好呀！",
            "tool_calls": [...],
            "tool_results": [...]
        }
    """

    def __init__(self):
        self.llm = LLMClient()
        self.memory = MemoryManager()
        self.tool_executor = ToolExecutor()
        self.system_prompt = SYSTEM_PROMPT + build_emotion_prompt()

    def chat(self, user_input: str) -> dict:
        self.memory.add_conversation("user", user_input)
        chat_history.add_message("user", user_input)
        bus.emit("user_message", user_input)

        context = self.memory.build_context(user_input)
        messages = self._prepare_messages(user_input, context)

        tools = registry.definitions_for_llm() if TOOLS_ENABLED else None
        all_tool_calls = None
        all_tool_results = None

        for round_i in range(MAX_TOOL_ROUNDS):
            response = self.llm.chat(messages, tools=tools)
            log.debug(
                "LLM round %d: content=%s tool_calls=%s",
                round_i,
                response.get("content", "")[:200],
                bool(response.get("tool_calls")),
            )

            if "tool_calls" in response and response["tool_calls"]:
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.get("content", ""),
                        "tool_calls": response["tool_calls"],
                    }
                )

                calls, results = self.tool_executor.execute_calls(
                    response["tool_calls"], messages
                )

                if all_tool_calls is None:
                    all_tool_calls = []
                    all_tool_results = []
                all_tool_calls.extend(calls)
                all_tool_results.extend(results)
            else:
                if all_tool_calls is None:
                    fallback_result = self._try_fallback(user_input)
                    if fallback_result:
                        return fallback_result
                # 无工具调用即为最终答复，必须跳出循环，
                # 否则会把同一轮请求重复送给 LLM（MAX_TOOL_ROUNDS 次）
                break
        return self._make_reply(response, all_tool_calls, all_tool_results)

    def chat_stream(self, user_input: str):
        """
        流式对话 - 逐块生成回复

        Yields:
            dict: {
                "type": "text" | "emotion" | "tool_call" | "tool_result" | "done",
                "content": "内容",
                "emotion": "情感标签",  # 仅当type="emotion"时
                "tool_calls": [...],    # 仅当type="tool_call"时
                "tool_results": [...]   # 仅当type="tool_result"时
            }
        """
        self.memory.add_conversation("user", user_input)
        chat_history.add_message("user", user_input)
        bus.emit("user_message", user_input)

        context = self.memory.build_context(user_input)
        messages = self._prepare_messages(user_input, context)

        tools = registry.definitions_for_llm() if TOOLS_ENABLED else None
        all_tool_calls = None
        all_tool_results = None
        full_content = ""
        tool_calls = None

        for round_i in range(MAX_TOOL_ROUNDS):
            full_content = ""
            tool_calls = None

            for chunk in self.llm.chat_stream(messages, tools=tools):
                if chunk["done"]:
                    # 工具调用由 LLM 层在流结束时一次性交回，无需二次推理
                    tool_calls = chunk.get("tool_calls")
                    break

                content = chunk.get("content", "")
                if content:
                    full_content += content
                    yield {"type": "text", "content": content}

            if tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": full_content,
                        "tool_calls": tool_calls,
                    }
                )

                calls, results = self.tool_executor.execute_calls(tool_calls, messages)

                if all_tool_calls is None:
                    all_tool_calls = []
                    all_tool_results = []
                all_tool_calls.extend(calls)
                all_tool_results.extend(results)

                yield {"type": "tool_call", "tool_calls": calls}
                yield {"type": "tool_result", "tool_results": results}
            else:
                if all_tool_calls is None:
                    fallback_result = self._try_fallback(user_input)
                    if fallback_result:
                        yield {"type": "emotion", "emotion": fallback_result["emotion"]}
                        yield {"type": "text", "content": fallback_result["text"]}
                        yield {"type": "done"}
                        return

                # 提取情感并生成最终回复
                emotion, clean_text, body_params = extract_emotion(full_content)
                self.memory.add_conversation("assistant", full_content)
                chat_history.add_message("assistant", full_content, emotion=emotion)

                yield {
                    "type": "emotion",
                    "emotion": emotion,
                    "body_params": body_params,
                }
                yield {"type": "done"}
                return

        # 如果达到最大轮数
        emotion, clean_text, body_params = extract_emotion(full_content)
        self.memory.add_conversation("assistant", full_content)
        chat_history.add_message("assistant", full_content, emotion=emotion)

        yield {"type": "emotion", "emotion": emotion, "body_params": body_params}
        yield {"type": "done"}

    def _prepare_messages(self, user_input: str, context: list[dict]) -> list[dict]:
        """组装发给 LLM 的消息列表。

        注意：`add_conversation` 已把本轮输入写入短期记忆，`build_context`
        会把它一并带出（位于 context 末尾）。若此处再无条件下追加，
        LLM 就会收到两条完全相同的 user 消息。因此只在未被带回时追加。
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(context)

        already_included = (
            bool(context)
            and context[-1].get("role") == "user"
            and context[-1].get("content") == user_input
        )
        if not already_included:
            messages.append({"role": "user", "content": user_input})

        return messages

    def _make_reply(self, response: dict, tool_calls, tool_results) -> dict:
        content = response.get("content", "")
        emotion, clean_text, body_params = extract_emotion(content)
        self.memory.add_conversation("assistant", content)
        chat_history.add_message("assistant", content, emotion=emotion)

        return {
            "emotion": emotion,
            "text": clean_text,
            "body_params": body_params,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
        }

    def _try_fallback(self, user_input: str) -> dict | None:
        for rule in FALLBACK_RULES:
            for pattern in rule["patterns"]:
                m = re.search(pattern, user_input)
                if m:
                    tool_name = rule["tool"]
                    if "extract_args" in rule:
                        args = rule["extract_args"](m)
                    else:
                        args = rule.get("args", {})
                    log.info("Fallback触发: %s %s", tool_name, args)
                    result = registry.execute(tool_name, args)
                    bus.emit("tool_call", tool_name, args)
                    bus.emit("tool_result", tool_name, result)
                    content = f"[gentle] {result}"
                    emotion, clean_text, body_params = extract_emotion(content)
                    # 保存助手回复到聊天记录
                    self.memory.add_conversation("assistant", content)
                    chat_history.add_message("assistant", content, emotion=emotion)
                    return {
                        "emotion": emotion,
                        "text": clean_text,
                        "body_params": body_params,
                        "tool_calls": [{"name": tool_name, "arguments": args}],
                        "tool_results": [{"name": tool_name, "result": result}],
                    }
        return None

    def get_memory_stats(self) -> dict:
        return self.memory.get_stats()

    def get_chat_history(self, limit: int = 50) -> list[dict]:
        """获取聊天记录"""
        return chat_history.get_history(limit)

    def clear_memory(self):
        self.memory.clear_short()

    def clear_chat_history(self):
        """清空聊天记录"""
        chat_history.clear()
