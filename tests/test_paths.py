from pathlib import Path

import pytest

from calibrate.engine import Session, load_case

CASE = load_case(Path(__file__).parent.parent / "cases" / "clti-01.yaml")
ALL_RF = ["statin_high_intensity", "antiplatelet", "smoking_cessation", "diabetes_management", "bp_management", "offloading"]


def start(topics=("statin", "smoking", "work_footwear"), corrections=None):
    s = Session(CASE)
    for t in topics:
        s.ask_patient(t)
    s.sign_note(corrections if corrections is not None else {"note_fix_statin", "note_fix_smoking", "note_fix_footwear"})
    return s


def ideal(s):
    s.decide(["order_noninvasive", "order_xray", "offloading", "wound_care_self"])
    s.decide(["noncompressible", "ischemic_by_tp", "wifi_correct", "revasc_workup"])
    s.decide(["order_creatinine", "order_cta", "vein_mapping_first", "order_angiogram"])
    s.decide(["endo_tibial"])
    s.decide(ALL_RF)
    return s


def test_ideal_path_heals():
    o = ideal(start()).outcome()
    assert o["healed"] and not o["major_amputation"] and not o["died"]
    assert o["events"] == ["The wound healed."]


def test_patient_never_invents():
    s = Session(CASE)
    assert s.ask_patient("chest_pain") is None
    assert s.order("ankle_mri_of_the_moon") == "Not available."


def test_wound_care_center_message():
    s = start()
    assert "no wound care center" in s.order("wound_care_center")


def test_enough_flow_goes_to_b1_then_rejoins():
    s = start()
    s.decide(["enough_flow"])
    assert s.node == "B1"
    assert "osteomyelitis" in s.order("xray_foot")
    assert s.order("mri_foot").startswith("Not indicated")
    s.decide(["revasc_workup"])
    assert s.node == "D3"
    s.decide(["vein_mapping_first", "order_angiogram"])
    s.decide(["endo_tibial"])
    s.decide(ALL_RF)
    o = s.outcome()
    assert "Second toe amputation (osteomyelitis)." in o["events"] and o["healed"]


def test_wound_care_referral_without_workup_goes_to_b1():
    s = start()
    s.decide(["wound_care_referral", "lipids_per_pcp", "diabetes_per_pcp"])
    assert s.node == "B1"


def test_b1b_gas_gangrene_terminal():
    s = start()
    s.decide(["enough_flow"])
    s.decide(["no_revasc_workup"])
    o = s.outcome()
    assert o["terminal_reason"] == "B1b" and o["major_amputation"]
    assert any("gas gangrene" in e for e in o["events"])


def test_accepting_abi_goes_to_b1():
    s = start()
    s.decide(["order_noninvasive"])
    s.decide(["perfusion_adequate"])
    assert s.node == "B1"


def test_angio_before_mapping_is_detour_not_fail():
    s = start()
    s.decide(["order_noninvasive"])
    s.decide(["ischemic_by_tp", "revasc_workup"])
    s.decide(["angio_before_mapping"])
    assert s.node == "D3b" and "vein_mapping" not in s.orders  # stops at the angiogram result
    r = s.decide(["order_vein_mapping"])
    assert s.node == "D4" and "detour_second_angiogram" in s.flags
    assert "vein_mapping" in r["results"]


def test_or_without_mapping_terminal_b2():
    s = start()
    s.decide(["order_noninvasive"])
    s.decide(["ischemic_by_tp", "revasc_workup"])
    s.decide(["bypass_without_mapping"])
    o = s.outcome()
    assert o["terminal_reason"] == "B2" and "PTFE was used" in o["events"][0]


def test_cta_without_creatinine_flagged():
    s = start()
    s.decide(["order_noninvasive"])
    s.decide(["revasc_workup"])
    s.decide(["order_cta", "vein_mapping_first", "order_angiogram"])
    assert "cta_without_creatinine" in s.flags


def test_d3_unclear_needs_followup():
    s = start()
    s.decide(["order_noninvasive"])
    s.decide(["revasc_workup"])
    r = s.decide(["order_cta"])
    assert r["needs_followup"] and s.node == "D3"


@pytest.mark.parametrize("missing,expect", [
    ("statin_high_intensity", "Myocardial infarction (LDL not managed)."),
    ("diabetes_management", "Below-knee amputation"),
    ("offloading", "Second toe amputation."),
])
def test_modifiers(missing, expect):
    s = start()
    d1 = ["order_noninvasive"] + ([] if missing == "offloading" else ["offloading"])
    s.decide(d1)
    s.decide(["revasc_workup"])
    s.decide(["vein_mapping_first", "order_angiogram"])
    s.decide(["endo_tibial"])
    s.decide([a for a in ALL_RF if a != missing])
    assert any(expect in e for e in s.outcome()["events"])


def test_per_pcp_counts_as_not_managed():
    s = start()
    s.decide(["order_noninvasive", "offloading"])
    s.decide(["revasc_workup"])
    s.decide(["vein_mapping_first", "order_angiogram"])
    s.decide(["endo_tibial"])
    s.decide(["statin_high_intensity", "antiplatelet", "smoking_cessation", "diabetes_per_pcp"])
    o = s.outcome()
    assert o["risk_factors"]["diabetes"] == "deferred" and o["major_amputation"]


def test_amputation_death_rule():
    s = start()
    s.decide(["enough_flow"])
    s.decide(["no_revasc_workup"])
    assert s.outcome()["died"]  # amputation + LDL and antiplatelet both missed


def test_amputation_mi_survives_with_one_miss():
    s = start()
    s.decide(["statin_high_intensity", "enough_flow"])
    s.decide(["no_revasc_workup"])
    o = s.outcome()
    assert not o["died"] and any("He survived" in e for e in o["events"])


def test_alert_a1_overreliance():
    s = start()
    s.decide(["order_noninvasive"])
    assert "A1" in s.alerts_shown
    s.open_alert("A1")
    s.decide(["perfusion_adequate"])
    cells = {i["id"]: i["cell"] for i in s.calibration()["items"]}
    assert cells["A1"] == "overreliance"


def test_alert_shown_not_opened():
    s = ideal(start())
    cells = {i["id"]: i["cell"] for i in s.calibration()["items"]}
    assert cells["A1"] == "alert not opened" and cells["A7"] == "alert not opened"


def test_best_cli_misapplied_before_vein_known():
    s = start()
    s.decide(["order_noninvasive"])
    s.decide(["revasc_workup"])
    assert s.query_assistant("revasc_strategy")["id"] == "A3"
    s.decide(["angio_before_mapping"])
    s.decide(["order_vein_mapping"])
    assert s.query_assistant("revasc_strategy")["id"] == "A3b"
    cells = {i["id"]: i["cell"] for i in s.calibration()["items"]}
    assert cells["A3"] == "overreliance"


def test_note_error_propagates_to_lipid_answer():
    s = start(corrections=set())  # signs everything uncorrected
    out = s.query_assistant("lipid_goal")
    assert out["id"] == "A4n"
    cells = {i["id"]: i["cell"] for i in s.calibration()["items"]}
    assert cells["N1"] == cells["N2"] == cells["N3"] == "overreliance"


def test_note_errors_only_if_triggered():
    s = start(topics=())
    assert s.triggered_note_errors() == []
    assert s.query_assistant("lipid_goal")["id"] == "A4"


def test_correct_advice_dismissed():
    s = ideal(start())
    s2 = start()
    s2.query_assistant("antiplatelet")
    s2.decide(["order_noninvasive", "offloading", "no_antiplatelet"])
    cells = {i["id"]: i["cell"] for i in s2.calibration()["items"]}
    assert cells["A5a"] == "reflexive dismissal"


def test_delayed_revasc_no_offloading_tma():
    s = start()
    s.decide(["enough_flow"])
    s.decide(["revasc_workup"])
    s.decide(["vein_mapping_first", "order_angiogram"])
    s.decide(["endo_tibial"])
    s.decide([a for a in ALL_RF if a != "offloading"])
    o = s.outcome()
    assert any("Transmetatarsal" in e for e in o["events"]) and not o["major_amputation"]


def _revasc_then(final):
    s = start()
    s.decide(["order_noninvasive", "offloading"] if "offloading" in final else ["order_noninvasive"])
    s.decide(["revasc_workup"])
    s.decide(["vein_mapping_first", "order_angiogram"])
    s.decide(["endo_tibial"])
    s.decide([a for a in final if a != "offloading"])
    return s.outcome()


def test_missed_smoking_impairs_healing_like_offloading():
    o = _revasc_then([a for a in ALL_RF if a != "smoking_cessation"])
    assert not o["healed"] and any("continued smoking" in e and "Second toe amputation." in e for e in o["events"])


def test_missed_antiplatelet_causes_mi_like_ldl():
    o = _revasc_then([a for a in ALL_RF if a != "antiplatelet"])
    assert o["healed"] and "Myocardial infarction (antiplatelet not started)." in o["events"]


def test_no_duplicate_mi_after_major_amputation():
    s = start()
    s.decide(["enough_flow"])
    s.decide(["no_revasc_workup"])
    ev = s.outcome()["events"]
    assert sum("nfarction" in e for e in ev) == 1


def test_lipid_panel_orderable_from_decision():
    s = start()
    r = s.decide(["order_noninvasive", "order_lipid_panel"])
    assert r["results"]["lipid_panel"] == "LDL 110 mg/dL"


def test_endo_before_vein_mapping_returns_with_new_wound():
    s = start()
    s.decide(["order_noninvasive", "offloading"])
    s.decide(["revasc_workup"])
    s.decide(["angio_before_mapping"])
    s.decide(["endo_tibial_before_mapping"])
    assert s.node == "D5"
    s.decide(ALL_RF)
    o = s.outcome()
    assert any("3 months later with another wound" in e for e in o["events"])


def test_bypass_at_d3b_is_b2():
    s = start()
    s.decide(["order_noninvasive"])
    s.decide(["revasc_workup"])
    s.decide(["angio_before_mapping"])
    s.decide(["bypass_without_mapping"])
    assert s.outcome()["terminal_reason"] == "B2"
