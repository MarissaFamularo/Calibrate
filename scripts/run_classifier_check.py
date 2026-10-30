"""Run the author-approved classifier check (cases/clti-01_classifier_check.md) against the live model.

Usage: python3 scripts/run_classifier_check.py [repeats]
Writes docs/classifier_check_results.md. Expected labels are engine action IDs after deterministic
sequencing (to_engine_actions); item 7 also checks order."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from calibrate.engine import load_case  # noqa: E402
from calibrate.llm import BasetenLLM  # noqa: E402
from calibrate.roles.classifier import classify, to_engine_actions  # noqa: E402

CASE = load_case(ROOT / "cases" / "clti-01.yaml")

ITEMS = [  # (node, resident text, expected status, expected engine actions, order matters)
    ("D1", "Foot's warm, I think he has enough flow. Dressing changes and see him back.", "clear", ["enough_flow", "wound_care_self"], False),
    ("D1", "Refer him to wound care and have his PCP handle the sugars and cholesterol.", "clear", ["wound_care_referral", "diabetes_per_pcp", "lipids_per_pcp"], False),
    ("D2", "ABI's 1.7, so inflow is fine. Ischemia isn't the problem here.", "clear", ["perfusion_adequate"], False),
    ("D2", "Ankles are noncompressible. Toe pressure 23, so he's ischemic. WIfI 1-3-1, needs a revasc workup.", "clear", ["noncompressible", "ischemic_by_tp", "wifi_correct", "revasc_workup"], False),
    ("D3", "I wouldn't bother with an MRI, but let's get a CTA.", "clear", ["order_cta"], False),
    ("D3", "Book him for an angiogram, we'll figure out vein later.", "clear", ["angio_before_mapping"], False),
    ("D3", "Check a creatinine, get bilateral vein mapping, then angio.", "clear", ["order_creatinine", "vein_mapping_first", "order_angiogram"], True),
    ("D3", "He's young, let's just take him for a fem-tibial bypass.", "clear", ["bypass_without_mapping"], False),
    ("D4", "Revascularize him and optimize everything.", "unclear", [], False),
    ("D5", "Atorvastatin 80, aspirin 81, refer to endo, and talk to him about quitting.", "clear", ["statin_high_intensity", "antiplatelet", "diabetes_management", "smoking_cessation"], False),
]


def main(repeats: int = 1):
    llm = BasetenLLM()
    rows, correct, total = [], 0, 0
    for i, (node, text, est, exp, ordered) in enumerate(ITEMS, 1):
        for rep in range(repeats):
            t0 = time.monotonic()
            out = classify(llm, CASE, node, text)
            dt = time.monotonic() - t0
            got = to_engine_actions(node, out["actions"], [])
            ok = out["status"] == est and (got == exp if ordered else sorted(got) == sorted(exp))
            correct += ok
            total += 1
            rows.append((i, rep + 1, node, text, est, exp, out["status"], got, out["followup"], ok, dt))
            print(f"#{i}.{rep + 1} {'OK ' if ok else 'MISS'} {node} {out['status']} {got} {out['followup']!r} {dt:.1f}s", flush=True)
    lat = sorted(r[-1] for r in rows)
    md = [f"# CLTI-01 classifier check: live results ({time.strftime('%Y-%m-%d %H:%M')})", "",
          f"Model: `{llm.cfg.model}`, reasoning_effort={llm.cfg.effort['classifier']}, seed={llm.cfg.seed}, temperature={llm.cfg.temperature}, repeats={repeats}.",
          f"**Agreement: {correct}/{total}** (exact match of status and action set; item 7 also order).",
          f"Latency per classification: median {lat[len(lat) // 2]:.1f}s, max {lat[-1]:.1f}s.", "",
          "| # | Run | Node | Resident says | Expected | Got | Follow-up | Match |", "|---|---|---|---|---|---|---|---|"]
    for i, rep, node, text, est, exp, st, got, fu, ok, dt in rows:
        e = "unclear" if est == "unclear" else ", ".join(exp)
        g = "unclear" if st == "unclear" else ", ".join(got) or "(none)"
        md.append(f"| {i} | {rep} | {node} | {text} | {e} | {g} | {fu or ''} | {'yes' if ok else '**NO**'} |")
    (ROOT / "docs" / "classifier_check_results.md").write_text("\n".join(md) + "\n")
    return correct, total


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
