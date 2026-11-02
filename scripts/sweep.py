"""Unscripted sweep: messy, varied residents. Flags follow-up loops, dead ends, and leaks. Usage: python3 scripts/sweep.py <scenario>"""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from calibrate import server
c = TestClient(server.app); T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)
S = {
 "terse": dict(mode="practice", talk=["hi whats going on", "pain?", "smoke?", "meds?", "feel pulses", "abi"],
   ap={"D1": "ischemic foot, abi falsly high, needs revasc. post op shoe, xray, dressings. asa statin quit smoking endo",
       "D3": "cr then mapping then angio", "D4": "angioplasty tibial", "D5": "asa, atorva 80, ldl<55, chantix, endo, bp meds"}),
 "per_pcp": dict(mode="assessment", talk=["What brings you in?", "Any pain in your legs?", "Do you smoke?", "Let me look at the wound and check pulses."],
   ap={"D1": "Wound care referral. Order ABI with toe pressures. PCP to manage diabetes and cholesterol.",
       "D2": "ABI is falsely elevated, toe pressures low. Needs angiogram.", "B1": "x-ray and angiogram",
       "D3": "angiogram", "D3b": "vein mapping", "D4": "balloon angioplasty of the AT", "D5": "aspirin, statin per PCP, quit smoking"}),
 "bypass": dict(mode="practice", talk=["What brings you in today?", "Do you smoke?", "Checking pulses", "ABI and toe pressures please"],
   ap={"D1": "Toe pressure 23 so ischemic despite ABI 1.7, WIfI 1-3-1. Surgical shoe, wound care, xray. Start aspirin and high intensity statin, smoking cessation, endocrine referral. Get a CTA after creatinine.",
       "D3": "He's young, take him for fem-tibial bypass."}),
 "visit1_orders": dict(mode="assessment", talk=["What brings you in?", "Do you take your medications?", "Do you smoke?", "What shoes do you wear at work?", "Exam: wound, pulses"],
   ap={"D1": "Order ABI and toe pressures, foot xray, surgical shoe, I will do wound care, vein mapping and angiogram. Atorvastatin 80, aspirin, smoking cessation, endocrinology.",
       "D2": "Non-compressible vessels, toe pressure shows ischemia, WIfI 1-3-1, proceed with revascularization workup.",
       "D3": "angiogram", "D3b": "vein mapping", "D4": "endovascular tibial angioplasty", "D5": "aspirin, atorvastatin 80 LDL<55, varenicline, endo referral, BP management"}),
}
sc = S[sys.argv[1]]; sid = c.post("/api/session", json={"mode": sc["mode"]}).json()["id"]
for q in sc["talk"]:
    r = c.post(f"/api/{sid}/talk", json={"text": q}).json(); log("SAY", q, "->", json.dumps(r["result"])[:200])
st = c.get(f"/api/{sid}/state").json()["state"]
for a in st["alerts_pending"]: c.post(f"/api/{sid}/alert/{a}")
st = c.post(f"/api/{sid}/finish_interview").json()["state"]; hist = st["note"]["history"]; first = True; fu = {}
for _ in range(25):
    st = c.get(f"/api/{sid}/state").json()["state"]
    if st["phase"] == "done": break
    if st["phase"] == "educator":
        ex = st["exchanges"][-1]; log("ATTENDING:", ex["text"][:220])
        c.post(f"/api/{sid}/educator", json={"text": "I'm not sure, can you explain?"}); continue
    n = st["note"]["node"]; fu[n] = fu.get(n, 0)
    if st["note"].get("followup"):
        fu[n] += 1; log("FOLLOWUP", n, fu[n], st["note"]["followup"])
        if fu[n] >= 3: log("!! LOOP at", n); break
    ap = sc["ap"].get(n)
    if ap is None: log("!! NO SCRIPTED A/P for node", n, st["note"]["prompt"]); break
    log("NOTE", n, "new:", [x["test"] for x in st["note"]["new_results"]])
    r = c.post(f"/api/{sid}/note", json={"ap": ap, "history": hist if first else None}).json(); first = False
    log("SIGN", n, "->", r["result"].get("node"), r["result"].get("followup") or "", (r["result"].get("consequence") or "")[:120])
st = c.get(f"/api/{sid}/state").json()["state"]
if st["phase"] == "done":
    rep = c.get(f"/api/{sid}/report").json()["result"]; t = json.dumps(rep)
    log("OUTCOME", rep["outcome"]["events"]); log("RF", rep["outcome"]["risk_factors"]); log("COUNTS", rep["calibration"]["counts"])
    log("CELLS", [(i["id"], i["cell"]) for i in rep["calibration"]["items"] if i["cell"] != "not consulted"])
    log("LEAKS", re.findall(r"\b(?!A1c\b)[AN]\d[a-z]?\b|planted", json.dumps(rep.get("debrief", {})) + json.dumps([d.get("educator") for d in rep["decisions"]])))
