"""Scripted stand-in for Muse, for UI development and demos without network.
Crude keyword routing; NOT a model of resident behavior. Enable with CALIBRATE_FAKE=1."""
from __future__ import annotations

import re

from .llm import FakeLLM

IDEAL = {
    "D1": ["order_noninvasive", "order_xray", "offloading", "wound_care_self", "order_lipid_panel"],
    "D2": ["noncompressible", "ischemic_by_tp", "wifi_correct", "revasc_workup"],
    "B1": ["order_xray", "revasc_workup"],
    "D3": ["order_creatinine", "order_vein_mapping", "order_angiogram"],
    "D4": ["endo_tibial"],
    "D5": ["statin_high_intensity", "antiplatelet", "smoking_cessation", "diabetes_management", "bp_management"],
}
WORDS = {
    "patient": {"wound_awareness": ["notice", "know", "found"], "pain": ["pain", "hurt", "cramp", "walk"],
                "work_footwear": ["work", "job", "shoe", "boot"], "statin": ["cholesterol", "statin"],
                "smoking": ["smok", "cigar", "tobacco"], "diabetes_care": ["diabet", "sugar", "endo"]},
    "exam": {"wound": ["wound", "ulcer", "look at"], "periwound": ["skin", "red", "around"],
             "foot_temperature": ["warm", "temperature", "feel"], "femoral_pulses": ["femoral", "pulses"],
             "popliteal_pulses": ["popliteal", "pulses"], "pedal_pulses": ["pedal", "dp", "pt ", "pulses"],
             "monofilament": ["monofilament", "sensation"], "footwear": ["shoe", "footwear", "sneaker"]},
}


def _hits(text, table):
    t = text.lower()
    return [k for k, ws in table.items() if any(w in t for w in ws)]


def responder(case):
    def r(role, messages, schema):
        sys, last = messages[0]["content"], messages[-1]["content"]
        props = schema.get("properties", {})
        if role == "patient":
            q = last.split("latest question:")[-1]
            exam_words = ("check", "examine", "look at", "feel", "palpate", "monofilament")
            exam = _hits(q, WORDS["exam"]) if any(w in q.lower() for w in exam_words) else []
            topics = [] if exam else _hits(q, WORDS["patient"])
            reply = "Okay." if exam else (" ".join(case["patient_script"][t] for t in topics) or "I'm not sure.")
            return {"topics": topics, "exam": exam, "exam_unmatched": False, "reply": reply}
        if role == "scribe":
            return {"hpi": case["chart"]["referral"], "pmh": "; ".join(case["chart"]["pmh"]),
                    "medications": "Metformin; metoprolol; statin", "allergies": case["chart"]["allergies"],
                    "social_history": "Wears appropriate footwear.", "vitals_labs": "BP 140/70; A1c 11"}
        if role == "verifier":
            return {"faithful": True, "problems": []} if "faithful" in props else {"problems": []}
        if role == "note_review":
            return {k: True for k in props}
        if role == "assistant_route":
            q = last.lower()
            for t, ws in {"wifi": ["wifi"], "revasc_strategy": ["bypass", "endo", "revasc"], "lipid_goal": ["ldl", "lipid", "statin"],
                          "antiplatelet": ["aspirin", "antiplatelet"], "blood_pressure": ["bp", "pressure"],
                          "diabetes": ["diabet", "a1c"], "smoking_cessation": ["smok"], "contrast_safety": ["contrast", "creat"]}.items():
                if any(w in q for w in ws):
                    return {"topic": t}
            return {"topic": "other"}
        if role == "assistant":
            m = re.search(r"CONTENT: (.*)\nCITATION: (.*)\n", last)
            if m:
                c, cit = m.group(1), m.group(2)
                return {"text": c + ("" if cit == "(none)" else f" ({cit})")}
            return {"text": "That is not in the available record."}
        if role == "classifier":
            node = next((n for n, d in case["nodes"].items() if d["prompt"] in sys), "D5")
            if "vague" in last.lower().split("resident:")[-1]:
                return {"status": "unclear", "actions": [], "followup": "Be specific. What exactly are you doing?"}
            allowed = set(props["actions"]["items"]["enum"])
            return {"status": "clear", "actions": [a for a in IDEAL[node] if a in allowed], "followup": ""}
        if role == "educator":
            if "decisions" in props:
                nodes = props["decisions"]["items"]["properties"]["node"]["enum"]
                return {"decisions": [{"node": n, "feedback": "(fake) Feedback vs rubric.", "ai_use_line": "(fake) AI-use line."} for n in nodes],
                        "overall": "(fake) Overall calibration summary."}
            kind = props["kind"]["enum"][0]
            msg = "(fake) Why did you choose that?" if kind == "question" else "(fake) Teaching point per the rubric."
            return {"kind": kind, "message": msg, "ai_use_line": "(fake) You did not consult the assistant here."}
        raise ValueError(role)
    return r


def fake_llm(case) -> FakeLLM:
    return FakeLLM(responder(case))
