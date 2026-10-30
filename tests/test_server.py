"""API walk with the scripted fake model: both modes reach a report; follow-ups amend the same note."""
import os

os.environ["CALIBRATE_FAKE"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from calibrate import server  # noqa: E402

c = TestClient(server.app)


def _walk(mode, tmp_path):
    server.SESSIONS_DIR = tmp_path
    sid = c.post("/api/session", json={"mode": mode}).json()["id"]
    r = c.post(f"/api/{sid}/talk", json={"text": "Let me check your pulses"}).json()
    assert [x["component"] for x in r["result"]["exam"]] == ["femoral_pulses", "popliteal_pulses", "pedal_pulses"]
    c.post(f"/api/{sid}/talk", json={"text": "Do you smoke?"})
    st = c.post(f"/api/{sid}/finish_interview").json()["state"]
    assert st["phase"] == "note" and st["note"]["history_editable"]
    r = c.post(f"/api/{sid}/note", json={"ap": "vague", "history": st["note"]["history"]}).json()
    assert r["result"]["followup"] and r["state"]["note"]["node"] == "D1"
    for _ in range(40):
        st = c.get(f"/api/{sid}/state").json()["state"]
        if st["phase"] == "done":
            break
        if st["phase"] == "educator":
            c.post(f"/api/{sid}/educator", json={"text": "because"})
            continue
        c.post(f"/api/{sid}/note", json={"ap": "plan"})
    assert st["phase"] == "done"
    assert [n["node"] for n in st["signed_notes"]] == ["D1", "D2", "D3", "D4", "D5"]
    assert "Addendum: plan" in st["signed_notes"][0]["ap"]
    rep = c.get(f"/api/{sid}/report").json()["result"]
    assert rep["outcome"]["events"] and all("what" in i for i in rep["calibration"]["items"])
    saved = c.get("/api/saved").json()
    assert saved and saved[0]["finished"]
    return rep


def test_practice_walk(tmp_path):
    assert "debrief" not in _walk("practice", tmp_path)


def test_assessment_walk(tmp_path):
    assert "debrief" in _walk("assessment", tmp_path)


def test_alert_requires_shown():
    sid = c.post("/api/session", json={"mode": "practice"}).json()["id"]
    assert c.post(f"/api/{sid}/alert/A1").status_code == 400
