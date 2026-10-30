"""Patient: answers the resident's interview questions ONLY from the case's patient script."""
from __future__ import annotations

from ..guards import generate_checked, unsupported_numbers
from ..llm import strict_object

SYSTEM = """You are role-playing a patient in a clinical training simulation (standardized-patient rules). A physician is interviewing and examining you.

Your facts are the SCRIPT (topics) and WHAT YOU KNOW ABOUT YOURSELF below. Nothing else about you is abnormal.

Rules:
- Decide which script topics the physician's latest question asks about. Report them in "topics" (empty list if none). Answer those in the patient's plain first-person voice; light paraphrase is fine, meaning exact.
- Questions answered by WHAT YOU KNOW ABOUT YOURSELF: answer from it (no topic to report).
- Anything else about symptoms, history, function, habits, or family: the answer is negative or normal. Deny it or say it's fine, briefly ("No." / "No, nothing like that." / "Yes, I can move them fine."). Never add a new problem or detail.
- Anything you would only know if a doctor told you (test results, numbers, diagnoses, what a doctor thinks): say nobody has told you.
- Do not volunteer topics the physician did not ask about. Greetings and small talk: brief and polite.
- Keep replies short (1-3 sentences), plain words, no medical jargon.
- EXAM: if the physician is performing or announcing a physical exam maneuver ("let me check your pulses", "I'm looking at the wound"), list the matching EXAM COMPONENTS in "exam" ("pulses" with no location = all pulse components), and just cooperate ("Okay."). If the maneuver matches none of them, set "exam_unmatched" true. Questions the physician asks YOU ("can you move your toes?") are not exam maneuvers: answer them. Never describe exam findings yourself."""


def _script_block(case: dict) -> str:
    gl = case.get("patient_topics", {})
    return "\n".join(f"- {t} ({gl.get(t, t)}): \"{a}\"" for t, a in case["patient_script"].items())


def answer(llm, case: dict, question: str, transcript: list[tuple[str, str]], max_regenerations: int = 2) -> dict:
    """Returns {"reply", "topics", "info"}. Caller passes topics to Session.ask_patient."""
    topics = list(case["patient_script"])
    comps = list(case["exam"])
    schema = strict_object({"topics": {"type": "array", "items": {"type": "string", "enum": topics}},
                            "exam": {"type": "array", "items": {"type": "string", "enum": comps}},
                            "exam_unmatched": {"type": "boolean"},
                            "reply": {"type": "string"}})
    eg = case.get("exam_topics", {})
    exam_block = "\n".join(f"- {c}: {eg.get(c, c)}" for c in comps)
    convo = "\n".join(f"{w}: {t}" for w, t in transcript[-12:]) or "(start of interview)"

    def gen(feedback):
        msgs = [{"role": "system", "content": SYSTEM + "\n\nSCRIPT:\n" + _script_block(case)
                    + "\n\nWHAT YOU KNOW ABOUT YOURSELF:\n" + "\n".join(f"- {k}" for k in case.get("patient_knows", []))
                    + "\n\nEXAM COMPONENTS:\n" + exam_block},
                {"role": "user", "content": f"Conversation so far:\n{convo}\n\nPhysician's latest question: {question}"}]
        if feedback:
            msgs.append({"role": "user", "content": "Your previous reply broke the rules: " + "; ".join(feedback)
                         + ". Answer again using only script facts."})
        return llm.json("patient", msgs, schema, "patient_reply")

    def check(out):
        probs = []
        used = [case["patient_script"][t] for t in out["topics"] if t in case["patient_script"]]
        extra = unsupported_numbers(out["reply"], *used, *case.get("patient_knows", []), question)
        if extra:
            probs.append(f"numbers not in the script: {sorted(extra)}")
        if not out["reply"].strip():
            probs.append("empty reply")
        return probs

    def fallback(last):
        # Topic routing was fine but wording kept drifting: read the script verbatim.
        ts = [t for t in (last or {}).get("topics", []) if t in case["patient_script"]]
        if ts:
            return {"topics": ts, "exam": [], "exam_unmatched": False, "reply": " ".join(case["patient_script"][t] for t in ts)}
        ex = [c for c in (last or {}).get("exam", []) if c in case["exam"]]
        return {"topics": [], "exam": ex, "exam_unmatched": False, "reply": "Okay." if ex else "No."}

    out, info = generate_checked(gen, check, max_regenerations, fallback)
    out["topics"] = list(dict.fromkeys(t for t in out["topics"] if t in case["patient_script"]))
    out["exam"] = list(dict.fromkeys(c for c in out.get("exam", []) if c in case["exam"]))
    out["exam_unmatched"] = bool(out.get("exam_unmatched")) and not out["exam"]
    return {**out, "info": info}
