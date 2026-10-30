"""Patient: answers the resident's interview questions ONLY from the case's patient script."""
from __future__ import annotations

from ..guards import generate_checked, unsupported_numbers
from ..llm import strict_object

SYSTEM = """You are role-playing a patient in a clinical training simulation. A physician is interviewing you.

You may ONLY state facts found in the SCRIPT below. Each script entry is a topic and what the patient says about it.

Rules:
- Decide which script topics the physician's latest question is asking about. Report them in "topics" (empty list if none).
- Answer only those topics, in the patient's plain first-person voice. Light paraphrase is fine; keep the meaning exact.
- Never add details that are not in the script: no extra symptoms, history, durations, numbers, medications, names, or feelings.
- Do not volunteer topics the physician did not ask about.
- If the question is not covered by any script topic, give a brief, natural non-answer ("I'm not sure," "I don't really know," "Nobody's told me about that") and report no topics. Never invent an answer.
- Greetings and small talk: reply briefly and politely, no medical content.
- Keep replies short (1-3 sentences). No medical jargon beyond what the script uses."""


def _script_block(case: dict) -> str:
    gl = case.get("patient_topics", {})
    return "\n".join(f"- {t} ({gl.get(t, t)}): \"{a}\"" for t, a in case["patient_script"].items())


def answer(llm, case: dict, question: str, transcript: list[tuple[str, str]], max_regenerations: int = 2) -> dict:
    """Returns {"reply", "topics", "info"}. Caller passes topics to Session.ask_patient."""
    topics = list(case["patient_script"])
    schema = strict_object({"topics": {"type": "array", "items": {"type": "string", "enum": topics}},
                            "reply": {"type": "string"}})
    convo = "\n".join(f"{w}: {t}" for w, t in transcript[-12:]) or "(start of interview)"

    def gen(feedback):
        msgs = [{"role": "system", "content": SYSTEM + "\n\nSCRIPT:\n" + _script_block(case)},
                {"role": "user", "content": f"Conversation so far:\n{convo}\n\nPhysician's latest question: {question}"}]
        if feedback:
            msgs.append({"role": "user", "content": "Your previous reply broke the rules: " + "; ".join(feedback)
                         + ". Answer again using only script facts."})
        return llm.json("patient", msgs, schema, "patient_reply")

    def check(out):
        probs = []
        used = [case["patient_script"][t] for t in out["topics"] if t in case["patient_script"]]
        extra = unsupported_numbers(out["reply"], *used, question)
        if extra:
            probs.append(f"numbers not in the script: {sorted(extra)}")
        if not out["reply"].strip():
            probs.append("empty reply")
        return probs

    def fallback(last):
        # Topic routing was fine but wording kept drifting: read the script verbatim.
        ts = [t for t in (last or {}).get("topics", []) if t in case["patient_script"]]
        if ts:
            return {"topics": ts, "reply": " ".join(case["patient_script"][t] for t in ts)}
        return {"topics": [], "reply": "I'm not sure."}

    out, info = generate_checked(gen, check, max_regenerations, fallback)
    out["topics"] = list(dict.fromkeys(t for t in out["topics"] if t in case["patient_script"]))
    return {**out, "info": info}
