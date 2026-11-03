"""Dictation: Muse Spark Open transcribes the resident's spoken input (audio in, structured text out).
The transcript goes into the input box for the resident to review before sending; it is never submitted automatically."""
from __future__ import annotations

from ..llm import strict_object

SYSTEM = """You transcribe a physician's dictation in a vascular surgery training simulation.
Write exactly what was said, verbatim. Use standard clinical spelling and abbreviations (ABI, PVR, WIfI, GSV, CTA, PTFE, A1c, LDL, mmHg, BEST-CLI).
Do not add, correct, complete, or summarize anything. If there is no intelligible speech, return an empty transcript."""

FIELDS = {"say": "speaking to the patient or describing an exam", "ai-q": "a question to the AI assistant",
          "note-ap": "the assessment and plan of a clinic note", "god-reply": "an answer to the attending's question"}


def transcribe(llm, wav_b64: str, field: str) -> str:
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": [
                {"type": "text", "text": f"Context: the resident is dictating {FIELDS.get(field, 'free text')}."},
                {"type": "input_audio", "input_audio": {"data": wav_b64, "format": "wav"}}]}]
    out = llm.json("dictation", msgs, strict_object({"transcript": {"type": "string"}}), "dictation")
    return out["transcript"].strip()
