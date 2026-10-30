"""Model-layer tests with a scripted fake model: guards, regeneration, fallbacks, sequencing,
and a full session walk. No network."""
from pathlib import Path

from calibrate.engine import TERMINAL
from calibrate.guards import unsupported_citations, unsupported_numbers
from calibrate.llm import FakeLLM
from calibrate.engine import load_case
from calibrate.roles import assistant, classifier, educator, patient, scribe
from calibrate.runtime import CaseRun

CASE = load_case(Path(__file__).parent.parent / "cases" / "clti-01.yaml")


# ---------- guards ----------
def test_number_guard():
    assert unsupported_numbers("ABI 1.7, TP 23", "ABI 1.7; toe pressure 23 mmHg") == set()
    assert unsupported_numbers("LDL goal under 70", "Target LDL < 100") == {"70"}
    assert unsupported_numbers("WIfI W1 I3 fI1", "W1 I0 fI1") == {"3"}


def test_citation_guard():
    assert unsupported_citations("Per BEST-CLI, go endo.", "BEST-CLI") == set()
    assert "basil-2" in unsupported_citations("BASIL-2 supports this.", "BEST-CLI")
    assert unsupported_citations("Per the guideline.", "") == {"guideline"}


# ---------- patient ----------
def test_patient_invented_number_falls_back_to_script():
    llm = FakeLLM({"patient": [{"topics": ["smoking"], "exam": [], "exam_unmatched": False, "reply": "Two packs a day for 40 years."}] * 3})
    out = patient.answer(llm, CASE, "Do you smoke?", [])
    assert out["reply"] == CASE["patient_script"]["smoking"] and out["info"]["fallback"]


def test_patient_unscripted_deflects():
    llm = FakeLLM({"patient": {"topics": [], "exam": [], "exam_unmatched": False, "reply": "No, nothing like that."}})
    out = patient.answer(llm, CASE, "Any chest pain?", [])
    assert out["topics"] == [] and not out["info"]["fallback"]


# ---------- scribe ----------
GOOD_NOTE = {"hpi": "58M referred by PCP for a toe wound he had not noticed.", "pmh": "DM (A1c 11); HTN",
             "medications": "Metformin; metoprolol; statin", "allergies": "NKDA",
             "social_history": "Works a job requiring a boot. Wears appropriate footwear.", "vitals_labs": "BP 140/70; A1c 11"}


def test_scribe_accepts_note_with_planted_errors():
    llm = FakeLLM({"scribe": [GOOD_NOTE], "verifier": [{"problems": []}]})
    d = scribe.draft(llm, CASE, [("Physician", "q"), ("Patient", "a")], ["N1", "N2", "N3"], {"statin", "smoking", "work_footwear"})
    assert not d["info"]["fallback"] and "Exam: Not captured" in d["text"]


def test_scribe_missing_planted_error_regenerates_then_falls_back():
    bad = dict(GOOD_NOTE, social_history="Smokes 1 ppd. Boot sometimes gets wet.")
    llm = FakeLLM({"scribe": [bad] * 3, "verifier": [{"problems": []}]})
    d = scribe.draft(llm, CASE, [], ["N2", "N3"], {"smoking", "work_footwear"})
    assert d["info"]["fallback"]
    assert scribe.planted_check(CASE, "N2", note=d["note"]) and scribe.planted_check(CASE, "N3", note=d["note"])
    assert "smok" not in d["text"].lower()


def test_fallback_note_applies_n1():
    n = scribe.fallback_note(CASE, {"statin"}, ["N1"])
    assert "Statin (ordered)" not in n["medications"] and "Statin" in n["medications"]
    assert "don't take" not in scribe.render_note(n)


def test_judge_unchanged_note_is_uncorrected_without_model():
    llm = FakeLLM({})
    assert scribe.judge_corrections(llm, CASE, "x", "x", ["N1"]) == {"N1": False} and not llm.calls


def test_judge_only_asks_model_when_check_fails():
    draft = scribe.render_note(GOOD_NOTE)
    edited = draft.replace("Works a job", "Smokes 1 ppd x 30 years. Works a job")
    llm = FakeLLM({"note_review": [{"N2": True}]})
    out = scribe.judge_corrections(llm, CASE, draft, edited, ["N1", "N2", "N3"])
    assert out == {"N1": False, "N2": True, "N3": False}
    assert list(llm.calls[0]["schema"]["properties"]) == ["N2"]


# ---------- assistant ----------
def test_assistant_unfaithful_render_falls_back_to_spec():
    spec = CASE["assistant"]["A4"]
    llm = FakeLLM({"assistant": [{"text": "Target LDL under 70."}] * 3})
    r = assistant.render_spec(llm, spec, "LDL goal?", verify_with_model=False)
    assert r["text"].startswith("Target LDL < 100") and r["info"]["fallback"]


def test_assistant_must_carry_citation():
    spec = CASE["assistant"]["A3"]
    llm = FakeLLM({"assistant": [{"text": "Go endovascular first."}, {"text": "Endovascular first; BEST-CLI supports that."}],
                   "verifier": [{"faithful": True, "problems": []}]})
    r = assistant.render_spec(llm, spec, "Open or endo?")
    assert "BEST-CLI" in r["text"] and r["info"]["attempts"] == 2


def test_offspec_cannot_cite():
    llm = FakeLLM({"assistant": [{"text": "Per the 2024 guideline, yes."}] * 3})
    r = assistant.answer_offspec(llm, "Is he a smoker?", "CHART: ...", verify_with_model=False)
    assert "guideline" not in r["text"]


# ---------- classifier ----------
def test_sequence_ids_vein_first():
    assert classifier.to_engine_actions("D3", ["order_creatinine", "order_vein_mapping", "order_angiogram"], []) == \
        ["order_creatinine", "vein_mapping_first", "order_angiogram"]


def test_sequence_ids_angio_first():
    assert classifier.to_engine_actions("D3", ["order_angiogram", "order_vein_mapping"], []) == \
        ["angio_before_mapping", "order_vein_mapping"]


def test_bypass_maps_to_terminal_conduit():
    assert classifier.to_engine_actions("D4", ["bypass"], []) == ["bypass_prosthetic"]


def test_unclear_drops_actions():
    llm = FakeLLM({"classifier": {"status": "unclear", "actions": ["endo_tibial"], "followup": "Open or endo?"}})
    out = classifier.classify(llm, CASE, "D4", "Revascularize him and optimize everything.")
    assert out["actions"] == [] and out["followup"] == "Open or endo?"


def test_clear_but_empty_becomes_unclear():
    llm = FakeLLM({"classifier": {"status": "clear", "actions": [], "followup": ""}})
    assert classifier.classify(llm, CASE, "D1", "Hmm.")["status"] == "unclear"


# ---------- educator ----------
def test_educator_forced_teaching_point_after_two_replies():
    llm = FakeLLM({"educator": {"kind": "teaching_point", "message": "Vein first.", "ai_use_line": "You took A3 on faith."}})
    ex = [("Educator", "q1"), ("Resident", "a1"), ("Educator", "q2"), ("Resident", "a2")]
    educator.socratic_turn(llm, CASE, "D3", {"text": "angio", "actions": [], "results": {}, "consequence": None}, [], ex)
    assert llm.calls[0]["schema"]["properties"]["kind"]["enum"] == ["teaching_point"]


def test_educator_missing_ai_line_falls_back():
    llm = FakeLLM({"educator": [{"kind": "question", "message": "Why?", "ai_use_line": ""}] * 2})
    t = educator.socratic_turn(llm, CASE, "D1", {"text": "x", "actions": [], "results": {}, "consequence": None},
                               ["Did not consult the AI assistant at this decision."], [])
    assert t["ai_use_line"] and t["kind"] == "teaching_point"


# ---------- full session walk ----------
PLAN = {
    "What is your plan": ["order_noninvasive", "order_xray", "offloading", "wound_care_self", "order_lipid_panel"],
    "Noninvasive results": ["noncompressible", "ischemic_by_tp", "wifi_correct", "revasc_workup"],
    "work up his anatomy": ["order_creatinine", "order_vein_mapping", "order_angiogram"],
    "Angiogram shows": ["endo_tibial"],
    "Before discharge": ["statin_high_intensity", "antiplatelet", "smoking_cessation", "diabetes_management", "bp_management"],
}


def responder(role, messages, schema):
    sys = messages[0]["content"]
    if role == "patient":
        q = messages[-1]["content"].lower().split("latest question:")[-1]
        t = "smoking" if "smok" in q else "statin" if "cholesterol" in q else None
        return {"topics": [t] if t else [], "exam": [], "exam_unmatched": False, "reply": CASE["patient_script"][t] if t else "No."}
    if role == "scribe":
        return dict(GOOD_NOTE, social_history="Not discussed.")
    if role == "verifier":
        return {"problems": []} if "problems" in schema["properties"] and "faithful" not in schema["properties"] \
            else {"faithful": True, "problems": []}
    if role == "note_review":
        return {k: True for k in schema["properties"]}
    if role == "assistant_route":
        return {"topic": "antiplatelet"}
    if role == "assistant":
        return {"text": "Single antiplatelet therapy is indicated per the 2024 ACC/AHA lower extremity PAD guideline."}
    if role == "classifier":
        for k, acts in PLAN.items():
            if k in sys:
                return {"status": "clear", "actions": acts, "followup": ""}
    if role == "educator":
        if "debrief" in sys:
            nodes = schema["properties"]["decisions"]["items"]["properties"]["node"]["enum"]
            return {"decisions": [{"node": n, "feedback": "ok", "ai_use_line": "ok"} for n in nodes], "overall": "ok"}
        return {"kind": schema["properties"]["kind"]["enum"][0], "message": "Why?", "ai_use_line": "You did not use it."}
    raise AssertionError(role)


def test_full_session_practice_and_assessment():
    for mode in ("practice", "assessment"):
        run = CaseRun(CASE, FakeLLM(responder), mode=mode)
        run.interview("Do you smoke?")
        run.interview("Do you take your cholesterol pill?")
        assert run.s.topics_asked == {"smoking", "statin"}
        draft = run.draft_note()
        run.sign_note(draft + "\nSmokes 1 ppd x 30 years. Not taking statin.")
        a = run.ask_assistant("Should he be on aspirin?")
        assert a["id"] == "A5a" and a["confidence"] == "High"
        for _ in range(5):
            r = run.decide("plan")
            if mode == "practice":
                assert r["educator"]["ai_use_line"]
        assert run.s.node == TERMINAL
        rep = run.report()
        assert rep["outcome"]["healed"], rep["outcome"]
        assert len(rep["decisions"]) == 5
        assert any("N2" in f for f in rep["decisions"][0]["ai_facts"])
        assert ("debrief" in rep) == (mode == "assessment")


def test_alert_badge_and_unopened_fact():
    run = CaseRun(CASE, FakeLLM(responder), mode="assessment")
    run.sign_note(run.draft_note())
    run.decide("plan")
    assert run.pending_alerts() == ["A1", "A7"]
    run.decide("plan")
    assert any("Alert A1 was available but not opened" in f for f in run.records[1]["ai_facts"])


def test_offspec_ungrounded_patient_fact_regenerates():
    llm = FakeLLM({"assistant": [{"text": "His toe pressure was 40, so order an angiogram."}, {"text": "Order ABI with toe pressures."}],
                   "verifier": [{"problems": ["toe pressure 40 not in record"]}, {"problems": []}]})
    r = assistant.answer_offspec(llm, "What next?", "CHART: no tests resulted")
    assert r["text"] == "Order ABI with toe pressures." and r["info"]["attempts"] == 2
