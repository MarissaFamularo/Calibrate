"""Live end-to-end smoke test of all six roles on one scripted CLTI-01 session.
Usage: python3 scripts/smoke_live.py [practice|assessment]. Prints each model output, latency, and fallbacks;
saves the session JSON under sessions/."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from calibrate.engine import load_case  # noqa: E402
from calibrate.llm import BasetenLLM  # noqa: E402
from calibrate.runtime import CaseRun  # noqa: E402


def show(label, text, info=None):
    fb = f"  [attempts={info['attempts']} fallback={info['fallback']} problems={info['problems']}]" if info else ""
    print(f"\n--- {label}{fb}\n{text}", flush=True)


def main(mode="assessment"):
    t0 = time.monotonic()
    run = CaseRun(load_case(ROOT / "cases" / "clti-01.yaml"), BasetenLLM(), mode=mode)
    for q in ["Hi, I'm one of the surgeons. Did you know you had this wound?", "Any pain in the foot, at rest or when you walk?",
              "What do you do for work? What shoes do you wear?", "Are you taking your cholesterol medicine?",
              "Do you smoke?", "Any chest pain or shortness of breath?"]:
        show(f"PATIENT <- {q}", run.interview(q))
    print("topics asked:", sorted(run.s.topics_asked), "triggered:", run.s.triggered_note_errors())
    draft = run.draft_note()
    show("SCRIBE DRAFT", draft, run.note["info"])
    edited = draft.replace("Social history:", "Social history: Smokes 1 ppd x 30 years.")  # fixes N2 only
    run.sign_note(edited)
    print("note corrections judged:", run.note_corrected)
    for q in ["What's his WIfI?", "Open bypass or endo for him?", "What LDL goal should I target?", "What was his referral for?"]:
        a = run.ask_assistant(q)
        show(f"ASSISTANT <- {q} [{a['id']} {a['confidence']} {a['citation']}]", a["text"], a["info"])
    for text in ["ABI, PVR and toe pressures, foot x-ray, surgical shoe, I'll do the dressings myself."]:
        r = run.decide(text)
        print("decide ->", r.get("node"), r.get("results"), r.get("followup"))
    print("pending alerts:", run.pending_alerts())
    a = run.open_alert("A1")
    show("ALERT A1 opened", a["text"], a["info"])
    for text in ["Noncompressible vessels, toe pressure 23 means he's ischemic, WIfI 1-3-1, start revascularization workup.",
                 "Creatinine, then vein mapping, then angiogram.",
                 "Revascularize him.", "Tibial angioplasty.",
                 "High-intensity statin, aspirin, smoking cessation, endocrine referral, and adjust his BP meds."]:
        r = run.decide(text)
        print("decide ->", r.get("node"), r.get("results"), r.get("followup") or "", r.get("consequence") or "")
        if "educator" in r:
            show("EDUCATOR", f"[{r['educator']['kind']}] {r['educator']['message']}\nAI-use: {r['educator']['ai_use_line']}", r["educator"]["info"])
    rep = run.report()
    print("\nOUTCOME:", rep["outcome"]["events"])
    print("CALIBRATION:", rep["calibration"]["counts"])
    if "debrief" in rep:
        for d in rep["debrief"]["decisions"]:
            show(f"DEBRIEF {d['node']}", f"{d['feedback']}\nAI-use: {d['ai_use_line']}")
        show("DEBRIEF overall", rep["debrief"]["overall"], rep["debrief"]["info"])
    p = run.save(ROOT / "sessions")
    calls = run.llm.calls
    by = {}
    for c in calls:
        by.setdefault(c["role"], []).append(c["seconds"])
    print(f"\nsaved {p.name}; {len(calls)} model calls, {time.monotonic() - t0:.0f}s total")
    for r_, s in by.items():
        print(f"  {r_}: n={len(s)} median={sorted(s)[len(s) // 2]:.1f}s max={max(s):.1f}s")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "assessment")
