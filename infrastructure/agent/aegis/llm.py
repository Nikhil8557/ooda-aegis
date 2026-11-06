"""One small client for every Meta model OODA-Aegis can use.

All three backends speak the OpenAI Chat Completions format, so the agent only
changes a base URL and a model name:

  * Meta open weights served locally by Ollama (default, no key needed):
    Llama 3.2 3B for the fast edge tier, Llama 3.1 8B for program repair.
  * Muse Glimmer 30B, Meta's open-weight model, self-hosted with llama.cpp
    (we run it on Kaggle's free 2x T4 GPUs). Set GLIMMER_BASE_URL.
  * Muse Spark 1.3 through the Meta Model API. Set MODEL_API_KEY.

The key, if any, is read from the environment and never logged.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
META_API_URL = os.getenv("META_API_BASE", "https://api.meta.ai/v1")


@dataclass
class ModelTier:
    role: str          # "edge" or "repair"
    label: str         # human name shown in the dashboard
    model: str         # model id sent to the server
    base_url: str
    api_key: str
    reasoning_line: str = ""   # Glimmer reads its reasoning strength from the system prompt
    token_scale: float = 1.0   # Glimmer reasons before answering, so it needs a bigger budget

    def public(self) -> dict[str, str]:
        return {"role": self.role, "label": self.label, "model": self.model,
                "endpoint": self.base_url.split("//")[-1].split("/")[0]}


def _meta_key() -> str | None:
    return os.getenv("MODEL_API_KEY") or os.getenv("META_API_KEY") or None


def resolve_tiers() -> dict[str, ModelTier]:
    """Pick the best available Meta model for each tier from the environment."""
    glimmer = os.getenv("GLIMMER_BASE_URL")
    key = _meta_key()

    if glimmer:
        edge = ModelTier("edge", "Muse Glimmer 30B (open weights, self-hosted)",
                         os.getenv("GLIMMER_MODEL", "muse-glimmer-30b"), glimmer, "local-only",
                         "Reasoning strength: low\n", 4.0)
    else:
        edge = ModelTier("edge", "Llama 3.2 3B (Meta open weights, local)",
                         os.getenv("EDGE_MODEL", "llama3.2:3b"), OLLAMA_URL, "ollama")

    if key:
        repair = ModelTier("repair", "Muse Spark 1.3 (Meta Model API)",
                           os.getenv("REPAIR_MODEL", "muse-spark-1.3"), META_API_URL, key)
    elif glimmer and os.getenv("GLIMMER_FOR_REPAIR", "1") == "1":
        repair = ModelTier("repair", "Muse Glimmer 30B (open weights, self-hosted)",
                           os.getenv("GLIMMER_MODEL", "muse-glimmer-30b"), glimmer, "local-only",
                           "Reasoning strength: medium\n", 4.0)
    else:
        repair = ModelTier("repair", "Llama 3.1 8B (Meta open weights, local)",
                           os.getenv("REPAIR_MODEL", "llama3.1:8b"), OLLAMA_URL, "ollama")
    return {"edge": edge, "repair": repair}


class ModelError(RuntimeError):
    pass


def parse_json(text: str) -> Any:
    """Pull the first JSON object out of a reply, tolerating ``` fences and prose."""
    text = (text or "").strip()
    if "```" in text:
        inner = text.split("```", 2)[1]
        text = inner[inner.find("{"):] if "{" in inner else inner
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ModelError(f"reply had no JSON object: {text[:160]!r}")
    return json.loads(text[start:end + 1])


def chat_json(tier: ModelTier, system: str, user: str, schema: dict[str, Any],
              name: str, max_tokens: int = 2500, temperature: float = 0.2) -> tuple[dict[str, Any], dict[str, Any]]:
    """Ask for JSON that matches `schema`. Falls back from strict schema to
    JSON mode to prompt-only, because servers differ in what they accept."""
    client = OpenAI(base_url=tier.base_url, api_key=tier.api_key, timeout=600, max_retries=1)
    messages = [
        {"role": "system", "content": tier.reasoning_line + system +
         "\nReply with one JSON object only, matching this JSON schema:\n" + json.dumps(schema)},
        {"role": "user", "content": user},
    ]
    formats: list[tuple[str, dict[str, Any] | None]] = [
        ("json_schema", {"type": "json_schema", "json_schema": {"name": name, "schema": schema}}),
        ("json_object", {"type": "json_object"}),
        ("prompt_only", None),
    ]
    last_error: Exception | None = None
    for mode, fmt in formats:
        kwargs: dict[str, Any] = {"model": tier.model, "messages": messages,
                                  "max_tokens": int(max_tokens * tier.token_scale), "temperature": temperature}
        if fmt:
            kwargs["response_format"] = fmt
        if "api.meta.ai" in tier.base_url:
            kwargs["reasoning_effort"] = "low" if tier.role == "edge" else "medium"
        started = time.perf_counter()
        try:
            reply = client.chat.completions.create(**kwargs)
        except Exception as exc:  # try the next, simpler format
            last_error = exc
            continue
        latency = (time.perf_counter() - started) * 1000
        content = reply.choices[0].message.content or ""
        try:
            data = parse_json(content)
        except Exception as exc:
            last_error = exc
            continue
        usage = getattr(reply, "usage", None)
        meta = {"model": tier.model, "label": tier.label, "format": mode, "latency_ms": round(latency),
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None)}
        return data, meta
    raise ModelError(f"{tier.model} gave no usable JSON: {last_error}")
