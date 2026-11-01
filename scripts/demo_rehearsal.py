"""Live rehearsal of the two demo runs (good, overreliant) through the API. Usage: python3 scripts/demo_rehearsal.py good|over [fake]"""
import json, sys, time, os
if len(sys.argv) > 2 and sys.argv[2] == "fake":
    os.environ["CALIBRATE_FAKE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from calibrate import server

RUN = sys.argv[1]
c = TestClient(server.app)
T0 = time.time()
def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)

INTERVIEW = ["What brings you in today?", "Are you taking all your medications?", "Do you smoke?",
             "What kind of shoes do you wear at work?", "Checking his pedal pulses.", "Getting an ABI and toe pressures now."]

GOOD = {
  "pre_note_assistant": ["What antiplatelet should he be on?", "How should I manage his blood pressure?", "How should I help him quit smoking?"],
  "corrections": [(r"Statin[^\n,]*", "Statin (prescribed, NOT taking)"), (r"(?m)^Social history:.*$", "Social history: Smokes 1 ppd x 30 years. Wears a work boot at work that sometimes gets wet.")],
  "ap": {
    "D1": "58M DM (A1c 11), HTN, 1 ppd smoker with full-thickness 2nd toe ulcer. Non-compressible ankle vessels; ABI 1.7 not reliable. TP 23 with flattened digit waveforms = ischemia. WIfI W1 I3 fI1, CLTI. Plan: surgical shoe offloading; local wound care, I will manage; foot X-ray; revascularization workup with vein mapping; start high-intensity statin, aspirin; smoking cessation counseling; endocrinology referral and diabetes management; BP management.",
    "D3": "Check creatinine before any contrast. Bilateral GSV vein mapping before angiogram. CTA runoff if creatinine allows.",
    "D4": "No adequate GSV. Angiogram with endovascular treatment of one tibial vessel, balloon angioplasty.",
    "D5": "Atorvastatin 80 mg, LDL goal <55. Aspirin 81 mg. Smoking cessation counseling and nicotine replacement. Endocrinology referral and diabetes management, I will follow A1c. BP management. Continue surgical shoe offloading and wound care.",
  },
  "assistant_at": {"D3": ["Should we go endovascular first for him?"]},
}
OVER = {
  "pre_note_assistant": [],
  "corrections": None,
  "ap": {
    "D1": "ABI 1.7, adequate perfusion. Local wound care and surgical shoe, follow up 2 weeks.",
    "B1": "Foot X-ray. Revascularization workup.",
    "D3": "Angiogram, endovascular first per BEST-CLI.",
    "D3b": "Vein mapping.",
    "D4": "No adequate GSV. Endovascular treatment of one tibial vessel, balloon angioplasty.",
    "D5": "Continue current statin per chart, LDL goal <100. Aspirin 81 mg. Endocrinology referral and diabetes management. BP management.",
  },
  "assistant_at": {"D3": ["Should we go endovascular first for him?"], "D5": ["What should his LDL goal be?"]},
}
P = GOOD if RUN == "good" else OVER

sid = c.post("/api/session", json={"mode": "practice"}).json()["id"]
for q in INTERVIEW:
    r = c.post(f"/api/{sid}/talk", json={"text": q}).json()
    log("RESIDENT:", q); log("  ->", json.dumps(r["result"])[:400])
st = c.get(f"/api/{sid}/state").json()["state"]
log("alerts_pending:", st["alerts_pending"])
for a in list(st["alerts_pending"]):
    r = c.post(f"/api/{sid}/alert/{a}").json(); log("OPEN ALERT", a, "->", json.dumps(r["result"])[:500])
for q in P["pre_note_assistant"]:
    r = c.post(f"/api/{sid}/assistant", json={"text": q}).json(); log("ASK:", q, "->", json.dumps(r["result"])[:600])
st = c.post(f"/api/{sid}/finish_interview").json()["state"]
hist = st["note"]["history"]; log("DRAFT HISTORY:\n" + hist)
import re
for old, new in (P["corrections"] or []):
    if re.search(old, hist):
        hist = re.sub(old, new, hist, count=1)
    else:
        log("CORRECTION TARGET NOT FOUND:", old); hist += "\n" + new
log("EDITED HISTORY:\n" + hist)
first = True
asked = set()
for _ in range(30):
    st = c.get(f"/api/{sid}/state").json()["state"]
    if st["phase"] == "done": break
    if st["phase"] == "educator":
        ex = st["exchanges"][-1] if st["exchanges"] else {}
        log("ATTENDING:", ex.get("text", "")[:400])
        r = c.post(f"/api/{sid}/educator", json={"text": "The toe pressure is low and the ankle vessels are non-compressible, so the ABI is falsely elevated."}).json()
        continue
    for a in list(st.get("alerts_pending", [])):
        r = c.post(f"/api/{sid}/alert/{a}").json(); log("OPEN ALERT", a, "->", json.dumps(r["result"])[:400])
    node = st["note"]["node"] if st.get("note") else st["node"]
    for q in P["assistant_at"].get(node, []):
        if (node, q) in asked: continue
        asked.add((node, q))
        r = c.post(f"/api/{sid}/assistant", json={"text": q}).json(); log("ASK @", node, q, "->", json.dumps(r["result"])[:600])
    ap = P["ap"].get(node)
    if ap is None:
        log("NO A/P SCRIPTED FOR NODE", node, json.dumps(st.get("note"))[:800]); break
    log("NOTE", node, "header/results:", json.dumps({k: v for k, v in (st.get("note") or {}).items() if k != "history"})[:700])
    r = c.post(f"/api/{sid}/note", json={"ap": ap, "history": hist if first else None}).json()
    first = False
    log("SIGN", node, "->", json.dumps(r["result"])[:500])
rep = c.get(f"/api/{sid}/report").json()["result"]
log("OUTCOME:", json.dumps(rep["outcome"], indent=1))
log("CALIBRATION:", json.dumps(rep["calibration"], indent=1)[:3000])
