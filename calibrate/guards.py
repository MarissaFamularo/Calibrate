"""Deterministic string checks run on every model output before it reaches the resident.

The model renders language; these checks stop it from adding numbers or citations
that are not in its source material."""
from __future__ import annotations

import re
from typing import Callable

_NUM = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?|(?<=[A-Za-z])\d+")
_CITE = re.compile(
    r"\b(?:[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+|ACC/AHA|AHA|ADA|ESC|ESVS|SVS|KDIGO|NICE|USPSTF|et al\.?|guidelines?|trials?)\b",
    re.IGNORECASE,
)


def numbers(text: str) -> set[str]:
    out = set()
    for n in _NUM.findall(text or ""):
        out.add(n.rstrip("0").rstrip(".") if "." in n else n)
    return out


def unsupported_numbers(text: str, *sources: str) -> set[str]:
    allowed = set().union(*(numbers(s) for s in sources)) if sources else set()
    return numbers(text) - allowed


def citation_terms(text: str) -> set[str]:
    return {m.lower().rstrip(".") for m in _CITE.findall(text or "")}


def unsupported_citations(text: str, *sources: str) -> set[str]:
    allowed = set().union(*(citation_terms(s) for s in sources)) if sources else set()
    # Singular/plural of the same word count as the same term.
    norm = lambda t: t.rstrip("s")
    allowed_n = {norm(a) for a in allowed}
    return {t for t in citation_terms(text) if norm(t) not in allowed_n}


def generate_checked(generate: Callable[[list[str]], object], check: Callable[[object], list[str]],
                     max_regenerations: int, fallback: Callable[[object], object]) -> tuple[object, dict]:
    """Generate, check, regenerate with the problems as feedback; fall back after the cap.
    `fallback(last_output_or_None)` builds the deterministic output.
    Returns (output, info) where info records attempts and any problems seen."""
    feedback: list[str] = []
    last = None
    history = []
    for attempt in range(max_regenerations + 1):
        try:
            out = generate(feedback)
        except Exception as e:  # model unavailable: use the deterministic fallback
            history.append([f"model error: {type(e).__name__}: {e}"])
            break
        problems = check(out)
        history.append(problems)
        last = out
        if not problems:
            return out, {"attempts": attempt + 1, "fallback": False, "problems": history}
        feedback = problems
    return fallback(last), {"attempts": len(history), "fallback": True, "problems": history}
