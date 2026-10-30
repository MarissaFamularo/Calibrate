"""FastAPI server for Calibrate. Run: uvicorn calibrate.server:app --port 8000
CALIBRATE_FAKE=1 uses the scripted fake model (no network) for UI work."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import ROOT
from .engine import load_case
from .runtime import CaseRun

CASE = load_case(ROOT / "cases" / "clti-01.yaml")
SESSIONS_DIR = ROOT / "sessions"
WEB = Path(__file__).parent / "web"
RUNS: dict[str, CaseRun] = {}

app = FastAPI(title="Calibrate")


@app.middleware("http")
async def no_cache(request, call_next):
    """Always revalidate page assets so a restarted server never runs against a stale cached script."""
    resp = await call_next(request)
    resp.headers["Cache-Control"] = "no-cache"
    return resp
app.mount("/static", StaticFiles(directory=WEB), name="static")


def _llm():
    if os.environ.get("CALIBRATE_FAKE"):
        from .fake import fake_llm
        return fake_llm(CASE)
    from .llm import BasetenLLM
    return BasetenLLM()


class NewSession(BaseModel):
    mode: str = "practice"


class Text(BaseModel):
    text: str


class Note(BaseModel):
    ap: str
    history: Optional[str] = None  # Optional, not str | None: pydantic evaluates this on Python 3.9 (macOS system Python)


def _run(sid: str) -> CaseRun:
    if sid not in RUNS:
        raise HTTPException(404, "Session not found. Start a new case.")
    return RUNS[sid]


def _do(sid: str, fn):
    run = _run(sid)
    try:
        result = fn(run)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if run.signed_notes:
        run.save(SESSIONS_DIR)
    return {"result": result, "state": run.state()}


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.post("/api/session")
def new_session(body: NewSession):
    if body.mode not in ("practice", "assessment"):
        raise HTTPException(400, "Mode must be practice or assessment.")
    sid = uuid.uuid4().hex[:12]
    RUNS[sid] = CaseRun(CASE, _llm(), mode=body.mode)
    return {"id": sid, "state": RUNS[sid].state()}


@app.get("/api/{sid}/state")
def state(sid: str):
    return {"state": _run(sid).state()}


@app.post("/api/{sid}/talk")
def talk(sid: str, body: Text):
    return _do(sid, lambda r: r.interview(body.text))


@app.post("/api/{sid}/finish_interview")
def finish_interview(sid: str):
    return _do(sid, lambda r: r.draft_note() if r.note is None else r.note["text"])


@app.post("/api/{sid}/note")
def sign(sid: str, body: Note):
    def f(r):
        out = r.submit_note(body.ap, body.history)
        return {k: v for k, v in out.items() if k != "educator"} | (
            {"educator": {k: out["educator"][k] for k in ("kind", "message", "ai_use_line")}} if "educator" in out else {})
    return _do(sid, f)


@app.post("/api/{sid}/assistant")
def ask(sid: str, body: Text):
    return _do(sid, lambda r: {k: v for k, v in r.ask_assistant(body.text).items() if k != "info"})


@app.post("/api/{sid}/alert/{oid}")
def alert(sid: str, oid: str):
    return _do(sid, lambda r: {k: v for k, v in r.open_alert(oid).items() if k != "info"})


@app.post("/api/{sid}/educator")
def educator_reply(sid: str, body: Text):
    return _do(sid, lambda r: {k: v for k, v in r.educator_reply(body.text).items() if k != "info"})


@app.get("/api/{sid}/report")
def report(sid: str):
    return _do(sid, lambda r: _clean_report(r.report()))


def _clean_report(rep: dict) -> dict:
    rep = json.loads(json.dumps(rep, default=lambda o: sorted(o) if isinstance(o, set) else str(o)))
    if "debrief" in rep:
        rep["debrief"].pop("info", None)
    for it in rep.get("calibration", {}).get("items", []):
        src = CASE["assistant"].get(it["id"]) or CASE["note_errors"].get(it["id"], {})
        it["what"] = src.get("content") or src.get("error", "")
        it["source"] = "note" if it["id"] in CASE["note_errors"] else ("alert" if src.get("kind") == "alert" else "assistant")
    for d in rep.get("decisions", []):
        for e in d.get("educator", []) or []:
            e.pop("info", None)
    return rep


@app.get("/api/saved")
def saved():
    out = []
    for p in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
        try:
            d = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        rep = d.get("report") or {}
        out.append({"name": p.stem, "mode": d.get("mode"), "started": d.get("started"),
                    "finished": bool(rep), "events": (rep.get("outcome") or {}).get("events"),
                    "counts": (rep.get("calibration") or {}).get("counts")})
    return out


@app.get("/api/saved/{name}")
def saved_one(name: str):
    p = SESSIONS_DIR / f"{Path(name).name}.json"
    if not p.exists():
        raise HTTPException(404, "Saved session not found.")
    d = json.loads(p.read_text())
    if not d.get("report"):
        raise HTTPException(400, "This session was not finished.")
    return _clean_report(d["report"])
