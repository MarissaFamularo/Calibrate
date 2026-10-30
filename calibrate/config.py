"""Runtime configuration. Provider is swappable here; keys come from .env and are never logged."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path = ROOT / ".env") -> None:
    """Minimal .env loader (KEY=VALUE lines). Does not override variables already set."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


@dataclass
class ModelConfig:
    base_url: str = "https://inference.baseten.co/v1"
    model: str = "meta-models/muse-spark-open-1026"  # hackathon key works ONLY with this ID
    api_key_env: str = "BASETEN_API_KEY"
    seed: int = 1026
    temperature: float = 0.2
    max_tokens: int = 4096
    timeout_s: float = 90.0
    # Reasoning effort per role (Muse Spark Open always reasons; lower = faster).
    effort: dict = field(default_factory=lambda: {
        "patient": "low",
        "scribe": "low",
        "assistant_route": "low",
        "assistant": "low",
        "verifier": "low",
        "classifier": "medium",
        "note_review": "low",
        "educator": "low",
    })
    # Model-based verification on top of deterministic string checks. Turn off to cut latency.
    verify_scribe_with_model: bool = True
    verify_assistant_with_model: bool = True
    max_regenerations: int = 2
