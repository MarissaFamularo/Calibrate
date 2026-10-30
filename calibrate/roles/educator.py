"""Educator. Practice mode: Socratic, max 2 exchanges, then a plain teaching point.
Assessment mode: silent during the case, then a per-decision debrief. Every piece of
feedback carries a mandatory AI-use line, built on deterministic facts from the engine."""
from __future__ import annotations

import yaml

from ..guards import generate_checked, unsupported_numbers
from ..llm import strict_object

MAX_EXCHANGES = 2

VOICE = """You are a vascular surgery attending teaching a resident in a case simulation that also trains calibrated trust in an AI clinical assistant.
Tone: brief, direct, no praise inflation, no filler. Talk to the resident ("you").
Use ONLY the facts provided (rubric, what the resident did, results, consequences, AI-use facts). Do not invent findings, results, outcomes, citations, or numbers. Do not predict future outcomes.
The AI assistant in this simulation is sometimes wrong on purpose. The AI-USE FACTS tell you which outputs were planted errors."""

PRACTICE = VOICE + """

MODE: practice (Socratic). Exchange {n} of at most {cap}.
{instruction}
"ai_use_line" (mandatory, one sentence): what the resident verified, took on faith, or ignored from the AI assistant at this decision, per the AI-USE FACTS. If they did not consult it, say so and whether that mattered here."""

Q_INSTR = """Ask ONE probing question that makes the resident examine the weakest part of their reasoning or their use of the AI assistant. kind = "question". Do not reveal the answer."""
TP_INSTR = """State the teaching point plainly in 2-4 sentences: what was right, what was wrong, and why, per the rubric. kind = "teaching_point"."""
EITHER_INSTR = """If the resident's last reply shows they now understand the key point, state the teaching point plainly (kind = "teaching_point"). Otherwise ask ONE more probing question (kind = "question")."""

DEBRIEF = VOICE + """

MODE: assessment debrief (end of case). For EACH decision listed, give "feedback" (2-4 sentences: what was right/wrong vs the rubric and why) and a mandatory "ai_use_line" (one sentence on how they used, verified, or ignored the AI assistant at that decision, per the AI-USE FACTS). Then "overall": 2-3 sentences on their calibration pattern across the case, citing the calibration counts. No questions."""


def _allowed_numbers_source(case: dict, *extra: str) -> str:
    return yaml.safe_dump(case) + "\n".join(extra)


def socratic_turn(llm, case: dict, node: str, decision: dict, ai_facts: list[str], exchanges: list[tuple[str, str]],
                  max_regenerations: int = 1) -> dict:
    """decision = {"text", "actions" (labels), "results", "consequence"}. exchanges = [(Educator|Resident, text)].
    Returns {"kind", "message", "ai_use_line", "info"}."""
    replies = sum(1 for w, _ in exchanges if w == "Resident")
    if replies == 0:
        instr = Q_INSTR
    elif replies >= MAX_EXCHANGES:
        instr = TP_INSTR
    else:
        instr = EITHER_INSTR
    forced_tp = instr is TP_INSTR
    facts = _facts_block(case, node, decision, ai_facts)
    convo = "\n".join(f"{w}: {t}" for w, t in exchanges) or "(none yet)"
    kinds = ["teaching_point"] if forced_tp else (["question"] if instr is Q_INSTR else ["question", "teaching_point"])
    schema = strict_object({"kind": {"type": "string", "enum": kinds}, "message": {"type": "string"},
                            "ai_use_line": {"type": "string"}})
    src = _allowed_numbers_source(case, decision["text"], convo)

    def gen(feedback):
        msgs = [{"role": "system", "content": PRACTICE.format(n=replies + 1, cap=MAX_EXCHANGES, instruction=instr)},
                {"role": "user", "content": f"{facts}\n\nSOCRATIC EXCHANGE SO FAR:\n{convo}"}]
        if feedback:
            msgs.append({"role": "user", "content": "Fix: " + "; ".join(feedback)})
        return llm.json("educator", msgs, schema, "educator_turn")

    def check(out):
        probs = []
        if not out["ai_use_line"].strip():
            probs.append("ai_use_line is mandatory")
        extra = unsupported_numbers(out["message"] + " " + out["ai_use_line"], src)
        if extra:
            probs.append(f"numbers not in the case: {sorted(extra)}")
        return probs

    def fallback(last):
        return {"kind": "teaching_point", "message": case["rubrics"][node],
                "ai_use_line": ai_facts[0] if ai_facts else "You did not consult the AI assistant at this decision."}

    out, info = generate_checked(gen, check, max_regenerations, fallback)
    return {**out, "info": info}


def debrief(llm, case: dict, decisions: list[dict], calibration: dict, outcome: dict, max_regenerations: int = 1) -> dict:
    """decisions = [{"node", "text", "actions", "results", "consequence", "ai_facts"}]."""
    nodes = [d["node"] for d in decisions]
    blocks = "\n\n".join(f"=== DECISION {d['node']} ===\n" + _facts_block(case, d["node"], d, d["ai_facts"]) for d in decisions)
    summary = ("CALIBRATION COUNTS (each count is one AI output or one AI-drafted note error, NOT a decision; "
               "'not consulted' = an assistant answer the resident never asked for): "
               f"{calibration['counts']}\n"
               f"OUTCOME EVENTS (fixed): {outcome['events']}")
    schema = strict_object({
        "decisions": {"type": "array", "items": strict_object({
            "node": {"type": "string", "enum": sorted(set(nodes)) or ["none"]},
            "feedback": {"type": "string"}, "ai_use_line": {"type": "string"}})},
        "overall": {"type": "string"}})
    src = _allowed_numbers_source(case, blocks, summary)

    def gen(feedback):
        msgs = [{"role": "system", "content": DEBRIEF},
                {"role": "user", "content": f"{blocks}\n\n{summary}"}]
        if feedback:
            msgs.append({"role": "user", "content": "Fix: " + "; ".join(feedback)})
        return llm.json("educator", msgs, schema, "debrief")

    def check(out):
        probs = []
        got = [d["node"] for d in out["decisions"]]
        if sorted(got) != sorted(nodes):
            probs.append(f"must cover each decision exactly once: {nodes}")
        if any(not d["ai_use_line"].strip() for d in out["decisions"]):
            probs.append("every decision needs an ai_use_line")
        text = " ".join(d["feedback"] + " " + d["ai_use_line"] for d in out["decisions"]) + " " + out["overall"]
        extra = unsupported_numbers(text, src)
        if extra:
            probs.append(f"numbers not in the case: {sorted(extra)}")
        return probs

    def fallback(last):
        return {"decisions": [{"node": d["node"], "feedback": case["rubrics"][d["node"]],
                               "ai_use_line": (d["ai_facts"] or ["You did not consult the AI assistant."])[0]} for d in decisions],
                "overall": f"Calibration counts: {calibration['counts']}."}

    out, info = generate_checked(gen, check, max_regenerations, fallback)
    return {**out, "info": info}


def _facts_block(case: dict, node: str, d: dict, ai_facts: list[str]) -> str:
    res = "\n".join(f"- {k}: {v}" for k, v in (d.get("results") or {}).items()) or "- (none)"
    return (f"DECISION PROMPT: {case['nodes'][node]['prompt']}\n"
            f"RUBRIC: {case['rubrics'][node]}\n"
            f"RESIDENT SAID: {d['text']}\n"
            f"CLASSIFIED AS: {', '.join(d.get('actions') or []) or '(nothing specific)'}\n"
            f"RESULTS RETURNED:\n{res}\n"
            f"CONSEQUENCE: {d.get('consequence') or '(case continues)'}\n"
            "AI-USE FACTS:\n" + ("\n".join(f"- {f}" for f in ai_facts) or "- Did not consult the AI assistant."))
