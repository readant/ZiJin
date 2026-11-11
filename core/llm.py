"""
大模型调用模块 - 支持 Ollama 和 OpenAI API

原理：
    封装不同 LLM 提供商的 API 调用，提供统一的接口。
    支持本地部署 (Ollama) 和云端服务 (OpenAI API)。

使用方法：
    client = LLMClient()
    response = client.chat([
        {"role": "user", "content": "你好"}
    ])
    print(response["content"])

配置：
    在 config/settings.py 中设置：
    - LLM_PROVIDER: "ollama" 或 "openai_api"
    - OLLAMA_BASE_URL: Ollama 服务地址
    - OLLAMA_MODEL: 使用的模型名称
    - OPENAI_API_KEY: OpenAI API 密钥
"""
import json
import ollama
import requests
from config.settings import (
    LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL,
    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
)
from core.log import get_logger

log = get_logger("llm")


class LLMClient:
    """
    大模型客户端 - 统一接口
    
    支持两种模式：
    1. Ollama - 本地部署，通过 HTTP 调用
    2. OpenAI API - 云端服务，通过 REST API 调用
    """

    def __init__(self):
        """初始化 LLM 客户端"""
        self.provider = LLM_PROVIDER
        
        if self.provider == "ollama":
            # Ollama 本地部署
            self.client = ollama.Client(host=OLLAMA_BASE_URL)
            self.model = OLLAMA_MODEL
        else:
            # OpenAI API (使用 requests 直接调用)
            self.client = None
            self.model = OPENAI_MODEL

    def chat(self, messages: list[dict], tools: list[dict] = None) -> dict:
        """
        发送对话请求
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            tools: 工具定义列表 (可选)，用于 function calling
            
        Returns:
            dict: {
                "content": "回复文本",
                "tool_calls": [...]  # 可选，工具调用列表
            }
        """
        if self.provider == "ollama":
            return self._chat_ollama(messages, tools)
        return self._chat_openai_api(messages, tools)
    
    def chat_stream(self, messages: list[dict], tools: list[dict] = None):
        """
        发送对话请求（流式输出）
        
        Args:
            messages: 消息列表
            tools: 工具定义列表 (可选)
            
        Yields:
            dict: {
                "content": "文本片段",
                "done": False  # 是否完成
            }
        """
        if self.provider == "ollama":
            yield from self._chat_ollama_stream(messages, tools)
        else:
            yield from self._chat_openai_api_stream(messages, tools)

    def _chat_ollama(self, messages: list[dict], tools: list[dict] = None) -> dict:
        """
        Ollama 本地调用
        
        Args:
            messages: 消息列表
            tools: 工具定义列表
            
        Returns:
            dict: LLM 回复
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "stream": False,  # 同步模式，等待完整回复
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.chat(**kwargs)
        message = response["message"]

        result = {"content": message.get("content", "")}
        
        # 检查是否有工具调用
        if "tool_calls" in message:
            result["tool_calls"] = message["tool_calls"]
        
        return result
    
    def _chat_ollama_stream(self, messages: list[dict], tools: list[dict] = None):
        """Ollama 流式调用"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.chat(**kwargs)

        # 流式模式下工具调用可能分散在多个 chunk 中，逐块累积而非丢弃
        collected_tool_calls = []
        for chunk in response:
            if "message" in chunk:
                message = chunk["message"]
                content = message.get("content", "")
                if content:
                    yield {"content": content, "done": False}

                if message.get("tool_calls"):
                    collected_tool_calls.extend(message["tool_calls"])

        # 流结束，把累积到的工具调用随 done 一起交回上层
        yield {"content": "", "done": True, "tool_calls": collected_tool_calls}

    def _chat_openai_api(self, messages: list[dict], tools: list[dict] = None) -> dict:
        """
        OpenAI API 调用 (通过 requests)
        
        Args:
            messages: 消息列表
            tools: 工具定义列表
            
        Returns:
            dict: LLM 回复
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        }
        payload = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools

        # 发送 POST 请求
        resp = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,  # 60秒超时
        )
        resp.raise_for_status()  # 如果状态码不是 200，抛出异常
        data = resp.json()
        
        # 提取回复
        choice = data["choices"][0]["message"]

        result = {"content": choice.get("content", "")}
        
        # 检查是否有工具调用
        if choice.get("tool_calls"):
            result["tool_calls"] = choice["tool_calls"]
        
        return result
    
    def _chat_openai_api_stream(self, messages: list[dict], tools: list[dict] = None):
        """OpenAI API 流式调用"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools

        # 发送 POST 请求（流式）
        resp = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
            stream=True,
        )
        resp.raise_for_status()

        # OpenAI 的 tool_calls 按 index 分片下发：name 与 arguments 均为增量，需拼接
        collected: dict[int, dict] = {}
        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                if data.strip() == '[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    choice = chunk["choices"][0]
                    delta = choice.get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield {"content": content, "done": False}

                    for tc in delta.get("tool_calls") or []:
                        idx = tc.get("index", 0)
                        slot = collected.setdefault(idx, {
                            "id": "", "type": "function",
                            "function": {"name": "", "arguments": ""},
                        })
                        if tc.get("id"):
                            slot["id"] = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            slot["function"]["name"] += fn["name"]
                        if fn.get("arguments"):
                            slot["function"]["arguments"] += fn["arguments"]
                except Exception as e:
                    log.debug("跳过无法解析的流式分片: %s", e)

        tool_calls = [collected[i] for i in sorted(collected)]
        yield {"content": "", "done": True, "tool_calls": tool_calls}
