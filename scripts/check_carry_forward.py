"""Live check: workup orders written in the visit-1 note are carried to the workup step. Usage: python3 scripts/check_carry_forward.py"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from calibrate import server
c = TestClient(server.app)
BASE = "Non-compressible ankle vessels, ABI unreliable, toe pressure 23 = ischemia, WIfI W1 I3 fI1. Surgical shoe, wound care myself, foot X-ray. High-intensity statin, aspirin, smoking cessation, endocrinology referral. "
CASES = {"angio_then_map": BASE + "Obtain angiogram. Obtain vein mapping.",
         "map_then_angio": BASE + "Bilateral vein mapping first, then angiogram.",
         "map_only": BASE + "Vein mapping."}
for name, ap in CASES.items():
    sid = c.post("/api/session", json={"mode": "assessment"}).json()["id"]
    for q in ["Do you smoke?", "Checking his pedal pulses.", "Getting an ABI and toe pressures now."]:
        c.post(f"/api/{sid}/talk", json={"text": q})
    st = c.post(f"/api/{sid}/finish_interview").json()["state"]
    r = c.post(f"/api/{sid}/note", json={"ap": ap, "history": st["note"]["history"]}).json()
    st = c.get(f"/api/{sid}/state").json()["state"]
    n = st["note"] or {}
    print(f"{name}: node={st['node']} note={n.get('node')} new_results={[x['test'] for x in n.get('new_results', [])]} prompt={n.get('prompt','')[:70]!r}")
