"""Ambient scribe: drafts the H&P from chart + interview transcript, inserting ONLY the
planted note errors whose trigger the patient actually said. Verified, regenerated, or
replaced by a deterministic fallback note."""
from __future__ import annotations

from ..context import chart_text, transcript_text
from ..guards import generate_checked, unsupported_citations, unsupported_numbers
from ..llm import strict_object

SECTIONS = [("hpi", "HPI"), ("pmh", "Past medical history"), ("medications", "Medications"),
            ("allergies", "Allergies"), ("social_history", "Social history"), ("vitals_labs", "Vitals / labs")]
EXAM_LINE = "Not captured by ambient documentation. Document your exam findings."

TYPE_HOW = {
    "attribution": "state the opposite of / misattribute what the patient said on this point",
    "omission": "leave this information out of the note entirely",
    "smoothing": "render the patient's qualified statement as a clean, reassuring fact",
}

SYSTEM = """You are an ambient clinical documentation AI (like Abridge). You draft a vascular surgery H&P from the CHART and the TRANSCRIPT of the clinician's interview.

Rules:
- Use ONLY facts in the chart and transcript. Do not add findings, exam results, diagnoses, assessments, plans, or numbers that are not there.
- You did not observe the physical exam; do not document any exam findings.
- Write in standard clinical third person, concise. Put every fact the patient said in the appropriate section.
- Sections: hpi, pmh, medications, allergies, social_history, vitals_labs. Use "Not discussed." for a section with no source facts.
- This is a training simulation. Apply EXACTLY the documentation errors listed under PLANNED ERRORS (if any), and make no other errors. Apply them naturally, as a real ambient tool would; do not flag them."""


def render_note(note: dict) -> str:
    parts = [f"{title}: {note.get(key, '').strip() or 'Not discussed.'}" for key, title in SECTIONS]
    parts.insert(5, f"Exam: {EXAM_LINE}")
    return "\n\n".join(parts)


def _contains_any(text: str, phrases: list[str]) -> bool:
    t = text.lower()
    return any(p.lower() in t for p in phrases)


def planted_check(case: dict, nid: str, note: dict | None = None, text: str | None = None) -> bool:
    """True if the planted error N<id> is present. Pass a sectioned note or plain text."""
    chk = case["note_error_checks"][nid]
    whole = text if text is not None else render_note(note)
    where = whole if note is None else note.get(chk["section"], "")
    if chk["must_contain_any"] and not _contains_any(where, chk["must_contain_any"]):
        return False
    return not _contains_any(whole, chk["must_not_contain_any"])


def fallback_note(case: dict, topics_asked: set[str], triggered: list[str]) -> dict:
    """Deterministic note: chart + verbatim script answers for topics the patient spoke to,
    with the triggered planted errors applied."""
    c = case["chart"]
    hidden = {case["note_errors"][n]["trigger_topic"] for n in triggered}
    said = [a for t, a in case["patient_script"].items() if t in topics_asked and t not in hidden]
    note = {
        "hpi": c["referral"] + (" Patient states: " + " ".join(f'"{s}"' for s in said) if said else ""),
        "pmh": "; ".join(c["pmh"]),
        "medications": "; ".join(c["meds"]),
        "allergies": c["allergies"],
        "social_history": "",
        "vitals_labs": "; ".join(f"{k.upper() if k == 'bp' else k} {v}" for k, v in c["vitals"].items())
                       + "; " + "; ".join(f"{k} {v}" for k, v in c["labs"].items()),
    }
    for n in triggered:
        ed = case["note_error_checks"][n].get("fallback_edit")
        if not ed:
            continue
        if "replace" in ed:
            note[ed["section"]] = note[ed["section"]].replace(*ed["replace"])
        if "append" in ed:
            note[ed["section"]] = (note[ed["section"]] + " " + ed["append"]).strip()
    return note


VERIFY_SYSTEM = """You audit an AI-drafted clinical note against its SOURCE (chart + interview transcript).
The note intentionally contains the EXPECTED ERRORS listed; ignore those.
Report every OTHER problem: any statement not supported by the source, any contradiction of the source, any exam finding (the scribe did not observe an exam), any added number, and any fact the patient stated in the transcript that is missing from the note (except omissions listed as expected).
Return an empty list if there are no other problems. Be precise; do not report style issues."""


def draft(llm, case: dict, transcript: list[tuple[str, str]], triggered: list[str], topics_asked: set[str], *,
          verify_with_model: bool = True, max_regenerations: int = 2) -> dict:
    """Returns {"note": sections, "text": rendered, "info"}."""
    src = f"CHART:\n{chart_text(case, include_notes=False)}\n\nTRANSCRIPT:\n{transcript_text(transcript)}"
    planned = [f"- {n} ({case['note_errors'][n]['type']}): {case['note_errors'][n]['error']}. "
               f"How: {TYPE_HOW[case['note_errors'][n]['type']]}." for n in triggered]
    planned_txt = "\n".join(planned) or "(none: the note must be fully accurate)"
    schema = strict_object({k: {"type": "string"} for k, _ in SECTIONS})
    vschema = strict_object({"problems": {"type": "array", "items": {"type": "string"}}})

    def gen(feedback):
        msgs = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"{src}\n\nPLANNED ERRORS:\n{planned_txt}"}]
        if feedback:
            msgs.append({"role": "user", "content": "Your previous draft had these problems; fix them. The PLANNED ERRORS must still be applied exactly as listed, "
                         "even if a problem below seems to ask otherwise: " + "; ".join(feedback)})
        return llm.json("scribe", msgs, schema, "hp_note")

    def check(note):
        probs = []
        text = render_note(note)
        for n in triggered:
            if not planted_check(case, n, note=note):
                probs.append(f"planned error {n} not applied as specified: {case['note_errors'][n]['error']}")
        extra = unsupported_numbers(text.replace(EXAM_LINE, ""), src)
        if extra:
            probs.append(f"numbers not in source: {sorted(extra)}")
        cites = unsupported_citations(text, src)
        if cites:
            probs.append(f"citations/guidelines not in source: {sorted(cites)}")
        if probs or not verify_with_model:
            return probs
        expected = "\n".join(
            f"- {case['note_errors'][n]['error']} (the source actually says: \"{case['patient_script'][case['note_errors'][n]['trigger_topic']]}\"). "
            "This misstatement/omission is intended: report NOTHING about this point." for n in triggered) or "(none)"
        v = llm.json("verifier", [{"role": "system", "content": VERIFY_SYSTEM},
                                  {"role": "user", "content": f"SOURCE:\n{src}\n\nEXPECTED ERRORS:\n{expected}\n\nNOTE:\n{text}"}],
                     vschema, "note_audit")
        return [p for p in v["problems"] if p.strip()]

    note, info = generate_checked(gen, check, max_regenerations, lambda last: fallback_note(case, topics_asked, triggered))
    return {"note": note, "text": render_note(note), "info": info}


JUDGE_SYSTEM = """A resident reviewed an AI-drafted note that contained known errors, edited it, and signed it.
For each listed error, decide whether the resident's edited note now CORRECTLY reflects what the patient actually said on that point.
Deleting the wrong statement without documenting the truth counts as corrected only if the note no longer asserts anything false on that point AND the clinically important fact is present. Replacing it with a different wrong statement is not corrected."""


def judge_corrections(llm, case: dict, draft_text: str, edited_text: str, triggered: list[str]) -> dict:
    """Returns {nid: bool corrected}. Deterministic first: if the planted error still passes its
    machine check in the edited text, it is uncorrected without asking the model."""
    result = {n: False for n in triggered}
    if edited_text.strip() == draft_text.strip():
        return result
    ask = [n for n in triggered if not planted_check(case, n, text=edited_text)]
    if not ask:
        return result
    truth = {n: case["patient_script"][case["note_errors"][n]["trigger_topic"]] for n in ask}
    schema = strict_object({n: {"type": "boolean"} for n in ask})
    errs = "\n".join(f"- {n}: note error = {case['note_errors'][n]['error']}; patient actually said: \"{truth[n]}\"" for n in ask)
    out = llm.json("note_review", [{"role": "system", "content": JUDGE_SYSTEM},
                                   {"role": "user", "content": f"ERRORS:\n{errs}\n\nEDITED NOTE:\n{edited_text}"}],
                   schema, "note_corrections")
    result.update({n: bool(out.get(n)) for n in ask})
    return result
