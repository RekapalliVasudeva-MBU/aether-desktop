"""LLM provider: OpenRouter (OpenAI-compatible chat + streaming).

Only OpenRouter is required by default. Users may set their own key/model via
config or env (OPENROUTER_API_KEY / AETHER_MODEL). The Hermes free-model policy
is respected: default is openrouter/free and we warn if a non-free model is used.
"""
from __future__ import annotations

import os
from typing import Iterator, List, Dict, Optional

from . import config


class ProviderError(RuntimeError):
    pass


def _client():
    from openai import OpenAI
    key = config.get_api_key()
    if not key:
        raise ProviderError(
            "No API key found. Set the OPENROUTER_API_KEY env var, "
            "or run `aether doctor --fix` to write your OWN key into Aether's .env, "
            "or paste it in the Providers panel."
        )
    # honour the active provider's base url (OpenRouter / OpenAI / Ollama / …)
    cfg = config.load_config()
    base = cfg["model"]["base_url"]
    return OpenAI(
        base_url=base,
        api_key=key,
        default_headers={
            "HTTP-Referer": "https://localhost/aether",
            "X-Title": "Aether Agent",
        },
    )


def default_model() -> str:
    return os.environ.get("AETHER_MODEL") or config.load_config()["model"]["default"]


def chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    stream: bool = False,
    temperature: Optional[float] = None,
    tools: Optional[List[Dict]] = None,
    tool_choice: Optional[str] = None,
    reasoning_effort: Optional[str] = None,
    extra: Optional[Dict] = None,
):
    cfg = config.load_config()
    model = model or default_model()
    # openrouter/free and *:free models are free; warn only for clearly paid ones
    if ":free" not in model and not model.startswith("openrouter/free"):
        print(f"[warn] model '{model}' is not a :free model; you may be billed.")
    temp = temperature if temperature is not None else cfg["model"]["temperature"]
    client = _client()
    kwargs = dict(
        model=model,
        messages=messages,
        temperature=temp,
        max_tokens=cfg["model"]["max_tokens"],
    )
    # Reasoning effort (OpenRouter reasoning.effort / Anthropic thinking).
    # "auto" means let the model decide -> don't pin anything.
    if reasoning_effort and reasoning_effort != "auto":
        if cfg["model"]["base_url"].rstrip("/").endswith("openrouter.ai/api/v1"):
            kwargs["extra_body"] = dict(kwargs.get("extra_body") or {},
                                       reasoning={"effort": reasoning_effort})
        else:
            kwargs["extra_body"] = dict(kwargs.get("extra_body") or {},
                                       thinking={"type": "enabled", "budget_tokens": 4096})
    if extra:
        # generic passthrough (e.g. other provider-specific knobs)
        kwargs["extra_body"] = dict(kwargs.get("extra_body") or {}, **extra)
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice or "auto"
    if stream:
        return client.chat.completions.create(**kwargs, stream=True)
    return client.chat.completions.create(**kwargs)


def stream_text(messages: List[Dict[str, str]], model: Optional[str] = None) -> Iterator[str]:
    """Yield text chunks from a streaming completion."""
    resp = chat(messages, model=model, stream=True)
    for chunk in resp:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


def complete(messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
    resp = chat(messages, model=model, stream=False)
    return resp.choices[0].message.content or ""
