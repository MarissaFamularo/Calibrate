"""Clinical AI assistant (ambient, Abridge-style). Spec'd topics and alerts render the
case-defined content (right or deliberately wrong); confidence and citation come from the
spec, never the model. Off-spec questions are answered from the chart only."""
from __future__ import annotations

from ..guards import citation_terms, generate_checked, numbers, unsupported_citations, unsupported_numbers
from ..llm import strict_object

OFFSPEC_CONFIDENCE = "Moderate"

ROUTE_SYSTEM = """You route a clinician's question to an AI clinical assistant topic.
Choose a topic ONLY if the question is specifically asking for that one thing (e.g., "What's his WIfI?", "Open or endo?", "What LDL goal?", "Should he be on aspirin?", "Is his creatinine OK for contrast?").
Broad or general questions go to "other": overall workup, what to order next, next steps, differential, general management, how to treat a diabetic foot ulcer, anything covering several topics.
Interpreting a test result (ABI, PVR, toe pressures, imaging, labs) goes to "other" unless the question asks for the WIfI stage itself.
Topics:
{topics}"""

RENDER_SYSTEM = """You are an ambient clinical AI assistant embedded in the EHR, answering a clinician.
This is a training simulation. Your answer content is fixed by the simulation and may be deliberately imperfect.

Convey EXACTLY the CONTENT below in 1-3 natural sentences that respond to the clinician:
- Keep every claim, value, and recommendation in the content, with the same meaning and certainty.
- Do NOT correct it, hedge it, add caveats, add other facts, numbers, or sources, or hint that it could be wrong.
- If a CITATION is given, mention it as the basis. If none is given, cite nothing.
- Do not state a confidence level (the interface shows it)."""

OFFSPEC_SYSTEM = """You are an ambient clinical decision-support AI embedded in the EHR, helping a vascular surgery resident with the current patient.
Use the RECORD for patient-specific facts and your general medical knowledge for recommendations. Be useful and brief: a direct, practical answer in at most 3 sentences or 4 short bullets.
- Never state a patient-specific finding, exam result, history, or test value that is not in the RECORD. If something needed has not been done or resulted, say so and recommend it if appropriate.
- You did not see the physical exam.
- Do not cite guidelines, trials, papers, or societies by name.
- Do not state a confidence level (the interface shows it)."""

GROUNDING_SYSTEM = """You check an AI assistant's RESPONSE against the patient RECORD.
General medical knowledge, recommendations, and standard thresholds are fine.
Problem = the response asserts a specific patient fact (a finding, exam result, history item, test value, or diagnosis) that is NOT in the RECORD, or contradicts the RECORD.
Not problems: recommendations, general knowledge, saying something has not been done or documented, or reasonable risk statements based on facts in the RECORD."""

FIDELITY_SYSTEM = """You check whether an AI assistant's RESPONSE faithfully conveys a fixed CONTENT statement.
The content may be clinically wrong on purpose (training simulation): judge ONLY fidelity, never clinical correctness.
Unfaithful = drops or changes a claim/value/recommendation, adds a new clinical claim, number, caveat, hedge, or source, or signals the content may be wrong."""


def route(llm, case: dict, question: str) -> str:
    topics = case.get("assistant_topics", {})
    schema = strict_object({"topic": {"type": "string", "enum": list(topics) + ["other"]}})
    listing = "\n".join(f"- {k}: {v}" for k, v in topics.items()) + "\n- other: anything else"
    out = llm.json("assistant_route", [{"role": "system", "content": ROUTE_SYSTEM.format(topics=listing)},
                                       {"role": "user", "content": question}], schema, "assistant_route")
    return out["topic"]


def render_spec(llm, output: dict, question: str | None, *, verify_with_model: bool = True,
                max_regenerations: int = 2) -> dict:
    """Render a spec'd output (topic answer or opened alert). Returns {"text", "info"}."""
    content, citation = output["content"], output.get("citation") or ""
    schema = strict_object({"text": {"type": "string"}})
    ask = question or "(No question: this is an unsolicited alert the clinician just opened. State it as an alert.)"
    vschema = strict_object({"faithful": {"type": "boolean"}, "problems": {"type": "array", "items": {"type": "string"}}})

    def gen(feedback):
        msgs = [{"role": "system", "content": RENDER_SYSTEM},
                {"role": "user", "content": f"CONTENT: {content}\nCITATION: {citation or '(none)'}\n\nClinician: {ask}"}]
        if feedback:
            msgs.append({"role": "user", "content": "Your previous answer was not faithful: " + "; ".join(feedback) + ". Try again."})
        return llm.json("assistant", msgs, schema, "assistant_answer")

    def check(out):
        text, probs = out["text"], []
        missing = numbers(content) - numbers(text)
        if missing:
            probs.append(f"dropped values from the content: {sorted(missing)}")
        extra = unsupported_numbers(text, content, citation, question or "")
        if extra:
            probs.append(f"added numbers: {sorted(extra)}")
        cites = unsupported_citations(text, content, citation)
        if cites:
            probs.append(f"added sources: {sorted(cites)}")
        need = citation_terms(citation) | citation_terms(content)
        if citation and need and not (citation_terms(text) & need):
            probs.append(f"did not mention the citation ({citation})")
        if probs or not verify_with_model:
            return probs
        v = llm.json("verifier", [{"role": "system", "content": FIDELITY_SYSTEM},
                                  {"role": "user", "content": f"CONTENT: {content}\nCITATION: {citation or '(none)'}\n\nRESPONSE: {text}"}],
                     vschema, "fidelity")
        return [] if v["faithful"] else (v["problems"] or ["unfaithful"])

    def fallback(last):
        return {"text": content + (f" ({citation})" if citation else "")}

    out, info = generate_checked(gen, check, max_regenerations, fallback)
    return {"text": out["text"], "info": info}


def answer_offspec(llm, question: str, record: str, max_regenerations: int = 2, verify_with_model: bool = True) -> dict:
    schema = strict_object({"text": {"type": "string"}})
    vschema = strict_object({"problems": {"type": "array", "items": {"type": "string"}}})

    def gen(feedback):
        msgs = [{"role": "system", "content": OFFSPEC_SYSTEM},
                {"role": "user", "content": f"RECORD:\n{record}\n\nClinician: {question}"}]
        if feedback:
            msgs.append({"role": "user", "content": "Your previous answer broke the rules: " + "; ".join(feedback) + ". Answer again."})
        return llm.json("assistant", msgs, schema, "assistant_answer")

    def check(out):
        cites = unsupported_citations(out["text"], record, question)
        if cites:
            return [f"named sources cited: {sorted(cites)}"]
        if not verify_with_model:
            return []
        v = llm.json("verifier", [{"role": "system", "content": GROUNDING_SYSTEM},
                                  {"role": "user", "content": f"RECORD:\n{record}\n\nRESPONSE: {out['text']}"}],
                     vschema, "grounding")
        return [p for p in v["problems"] if p.strip()]

    def fallback(last):
        return {"text": "I can't answer that reliably from the available record."}

    out, info = generate_checked(gen, check, max_regenerations, fallback)
    return {"text": out["text"], "info": info}
