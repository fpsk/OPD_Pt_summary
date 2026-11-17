"""
Shared client for the OpenAI-compatible LLM server (vLLM).

Every LLM call in the app goes through `chat_completion` so model, host,
timeouts and response parsing are configured in exactly one place.
"""

import json
import urllib.request
from typing import Any, Dict, List

import config


class LlmError(RuntimeError):
    """Raised when the LLM is unreachable or returns no usable text."""


def chat_completion(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 1500,
    timeout: float = 45,
    model: str = None,
) -> str:
    """Send a chat request and return the assistant text.

    Reasoning models (e.g. gpt-oss) may leave `content` empty and put text in
    `reasoning_content` / `reasoning`; those are used as a fallback.
    """
    payload = {
        "model": model or config.LOCAL_LLM_DEFAULT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        f"{config.LOCAL_LLM_HOST}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body: Dict[str, Any] = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise LlmError(str(e)) from e

    msg = (body.get("choices") or [{}])[0].get("message", {}) or {}
    text = (msg.get("content") or "").strip()
    if not text:
        text = (msg.get("reasoning_content") or msg.get("reasoning") or "").strip()
    return text


def is_online(timeout: float = 2) -> bool:
    """True if the LLM server answers its /models endpoint."""
    try:
        with urllib.request.urlopen(f"{config.LOCAL_LLM_HOST}/models", timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_model_name(timeout: float = 2) -> str:
    """Query /models to extract the active model name, or fallback to default."""
    try:
        with urllib.request.urlopen(f"{config.LOCAL_LLM_HOST}/models", timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("data", [])
                if models and "id" in models[0]:
                    return models[0]["id"]
    except Exception:
        pass
    return config.LOCAL_LLM_DEFAULT_MODEL
