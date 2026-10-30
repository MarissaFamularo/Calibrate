"""Clinical AI assistant (ambient, Abridge-style). Spec'd topics and alerts render the
case-defined content (right or deliberately wrong); confidence and citation come from the
spec, never the model. Off-spec questions are answered from the chart only."""
from __future__ import annotations

from ..guards import citation_terms, generate_checked, numbers, unsupported_citations, unsupported_numbers
from ..llm import strict_object

OFFSPEC_CONFIDENCE = "Moderate"

ROUTE_SYSTEM = """You route a clinician's question to an AI clinical assistant topic.
Pick the single topic the question is mainly about, or "other" if none fits. Topics:
{topics}"""

RENDER_SYSTEM = """You are an ambient clinical AI assistant embedded in the EHR, answering a clinician.
This is a training simulation. Your answer content is fixed by the simulation and may be deliberately imperfect.

Convey EXACTLY the CONTENT below in 1-3 natural sentences that respond to the clinician:
- Keep every claim, value, and recommendation in the content, with the same meaning and certainty.
- Do NOT correct it, hedge it, add caveats, add other facts, numbers, or sources, or hint that it could be wrong.
- If a CITATION is given, mention it as the basis. If none is given, cite nothing.
- Do not state a confidence level (the interface shows it)."""

OFFSPEC_SYSTEM = """You are an ambient clinical AI assistant embedded in the EHR, answering a clinician about the current patient.
Answer accurately and briefly (1-3 sentences) using ONLY the RECORD below (chart, interview/note, and resulted tests).
- If the record does not contain what is asked, say it is not in the available record.
- Do not mention any test result that is not in the record. You did not see the physical exam.
- Do not cite guidelines, trials, or other sources. Do not state numbers that are not in the record.
- Do not state a confidence level (the interface shows it)."""

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


def answer_offspec(llm, question: str, record: str, max_regenerations: int = 2) -> dict:
    schema = strict_object({"text": {"type": "string"}})

    def gen(feedback):
        msgs = [{"role": "system", "content": OFFSPEC_SYSTEM},
                {"role": "user", "content": f"RECORD:\n{record}\n\nClinician: {question}"}]
        if feedback:
            msgs.append({"role": "user", "content": "Your previous answer broke the rules: " + "; ".join(feedback) + ". Answer again."})
        return llm.json("assistant", msgs, schema, "assistant_answer")

    def check(out):
        probs = []
        extra = unsupported_numbers(out["text"], record, question)
        if extra:
            probs.append(f"numbers not in the record: {sorted(extra)}")
        cites = unsupported_citations(out["text"], record, question)
        if cites:
            probs.append(f"sources cited: {sorted(cites)}")
        return probs

    def fallback(last):
        return {"text": "I can't answer that reliably from the available record."}

    out, info = generate_checked(gen, check, max_regenerations, fallback)
    return {"text": out["text"], "info": info}
