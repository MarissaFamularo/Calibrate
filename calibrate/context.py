"""Plain-text renderings of case state for model prompts. Only what a role is allowed to see."""
from __future__ import annotations


def chart_text(case: dict) -> str:
    c = case["chart"]
    lines = [f"Referral: {c['referral']}",
             "PMH: " + "; ".join(c["pmh"]),
             "Medications: " + "; ".join(c["meds"]),
             f"Allergies: {c['allergies']}",
             "Vitals: " + "; ".join(f"{k.upper() if k == 'bp' else k}: {v}" for k, v in c["vitals"].items()),
             "Labs: " + "; ".join(f"{k} {v}" for k, v in c["labs"].items())]
    lines += [f"Chart note: {n}" for n in c["notes"]]
    return "\n".join(lines)


def transcript_text(transcript: list[tuple[str, str]]) -> str:
    if not transcript:
        return "(no interview recorded)"
    return "\n".join(f"{who}: {text}" for who, text in transcript)


def results_text(case: dict, orders: list[str], results: dict[str, str]) -> str:
    """Results of tests the resident actually ordered (never unordered ones)."""
    seen, lines = set(), []
    for o in orders:
        if o in seen or o not in results:
            continue
        seen.add(o)
        lines.append(f"{o}: {results[o]}")
    return "\n".join(lines) if lines else "(no tests resulted)"
