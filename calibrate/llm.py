"""Model client. Every call returns parsed JSON validated against a strict JSON schema.

`BasetenLLM` talks to Muse Spark Open (OpenAI-compatible API). `FakeLLM` returns scripted
responses for tests. Both expose `.json(role, messages, schema, name)` and record `.calls`.
"""
from __future__ import annotations

import json
import os
import time
from typing import Callable

from .config import ModelConfig, load_env


class LLMError(RuntimeError):
    pass


def strict_object(properties: dict, required: list[str] | None = None) -> dict:
    """JSON-schema object with strict-mode requirements (all keys required, no extras)."""
    return {"type": "object", "properties": properties,
            "required": required if required is not None else list(properties), "additionalProperties": False}


class BasetenLLM:
    def __init__(self, cfg: ModelConfig | None = None):
        from openai import OpenAI  # imported lazily so tests run without the SDK

        self.cfg = cfg or ModelConfig()
        load_env()
        key = os.environ.get(self.cfg.api_key_env)
        if not key:
            raise LLMError(f"{self.cfg.api_key_env} not set (expected in .env)")
        self.client = OpenAI(base_url=self.cfg.base_url, api_key=key, timeout=self.cfg.timeout_s, max_retries=0)
        self.calls: list[dict] = []

    def json(self, role: str, messages: list[dict], schema: dict, name: str, effort: str | None = None) -> dict:
        effort = effort or self.cfg.effort.get(role, "low")
        max_tokens = self.cfg.max_tokens
        last_err = None
        for attempt in range(4):
            t0 = time.monotonic()
            try:
                resp = self.client.chat.completions.create(
                    model=self.cfg.model, messages=messages, seed=self.cfg.seed,
                    temperature=self.cfg.temperature, max_tokens=max_tokens,
                    response_format={"type": "json_schema",
                                     "json_schema": {"name": name, "schema": schema, "strict": True}},
                    extra_body={"reasoning_effort": effort},
                )
            except Exception as e:  # rate limit / server / network: back off and retry
                status = getattr(e, "status_code", None)
                last_err = f"{type(e).__name__} {status or ''}".strip()
                if status in (400, 401, 403, 404):
                    raise LLMError(f"{role}: {last_err}: {getattr(e, 'message', e)}") from e
                time.sleep(1.5 * 2 ** attempt)
                continue
            dt = time.monotonic() - t0
            ch = resp.choices[0]
            usage = resp.usage
            rec = {"role": role, "seconds": round(dt, 2), "finish": ch.finish_reason, "effort": effort,
                   "prompt_tokens": getattr(usage, "prompt_tokens", None),
                   "completion_tokens": getattr(usage, "completion_tokens", None),
                   "reasoning_tokens": getattr(getattr(usage, "completion_tokens_details", None), "reasoning_tokens", None)}
            self.calls.append(rec)
            if ch.finish_reason == "length":
                last_err = "truncated"
                max_tokens = min(max_tokens * 2, 16384)
                continue
            try:
                return json.loads(ch.message.content)
            except (TypeError, json.JSONDecodeError):
                last_err = "invalid JSON"
                continue
        raise LLMError(f"{role}: failed after retries ({last_err})")


class FakeLLM:
    """Scripted model for tests. `responder(role, messages, schema)` returns the dict to emit,
    or pass a dict mapping role -> list of responses (consumed in order)."""

    def __init__(self, responder: Callable | dict):
        self.responder = responder
        self.calls: list[dict] = []

    def json(self, role, messages, schema, name, effort=None):
        self.calls.append({"role": role, "messages": messages, "schema": schema})
        if callable(self.responder):
            return self.responder(role, messages, schema)
        queue = self.responder[role]
        return queue.pop(0) if isinstance(queue, list) else queue
