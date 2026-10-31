"""Deterministic case engine for Calibrate.

The engine owns every fact, result, branch, outcome, and score. Model roles
(patient, scribe, assistant, classifier, educator) only render language and map
free text to the action IDs defined in the case spec.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

TERMINAL = "DONE"

# Decision actions that imply placing an order.
ACTION_ORDERS = {
    "order_noninvasive": ["abi_pvr", "toe_pressure"],
    "order_xray": ["xray_foot"],
    "order_mri": ["mri_foot"],
    "order_creatinine": ["creatinine"],
    "order_cta": ["cta_runoff"],
    "order_vein_mapping": ["vein_mapping"],
    "vein_mapping_first": ["vein_mapping"],
    "order_angiogram": ["angiogram"],
    "angio_before_mapping": ["angiogram"],
    "wound_care_referral": ["wound_care_center"],
    "order_lipid_panel": ["lipid_panel"],
    "order_a1c": ["a1c"],
}
REVASC_WORKUP = {"order_noninvasive", "revasc_workup", "order_cta", "order_angiogram", "vein_mapping_first"}


def load_case(path: str | Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


@dataclass
class Session:
    case: dict
    mode: str = "practice"  # practice | assessment
    node: str = "ENCOUNTER"
    topics_asked: set = field(default_factory=set)
    exam_done: set = field(default_factory=set)
    orders: list = field(default_factory=list)  # ordered list of order ids
    note_corrections: set = field(default_factory=set)
    note_signed: bool = False
    actions: list = field(default_factory=list)  # (node, action) in order
    assistant_seen: list = field(default_factory=list)  # (output_id, via)
    alerts_shown: list = field(default_factory=list)
    alerts_opened: list = field(default_factory=list)
    flags: set = field(default_factory=set)
    terminal_reason: str | None = None
    log: list = field(default_factory=list)

    # ---------- encounter ----------
    def ask_patient(self, topic: str) -> str | None:
        """Returns the scripted answer, or None (model must deflect, never invent)."""
        self._log("ask_patient", topic)
        ans = self.case["patient_script"].get(topic)
        if ans is not None:
            self.topics_asked.add(topic)
        return ans

    def examine(self, component: str) -> str | None:
        self._log("examine", component)
        finding = self.case["exam"].get(component)
        if "B1" in self.flags and component in self.case.get("exam_after_b1", {}):
            finding = self.case["exam_after_b1"][component]
        if finding is not None:
            self.exam_done.add(component)
        return finding

    def order(self, test: str) -> str:
        self._log("order", test)
        spec = self.case["orders"].get(test)
        self.orders.append(test)
        if spec is None:
            return self.case["default_order_result"]
        after_b1 = "B1" in self.flags
        if after_b1 and "result_after_b1" in spec:
            return spec["result_after_b1"]
        if after_b1 and "not_indicated_after_b1" in spec:
            self.flags.add("low_value_mri")
            return spec["not_indicated_after_b1"]
        if "message" in spec:
            return spec["message"]
        if "result" in spec:
            self._refresh_alerts()
            return spec["result"]
        return self.case["default_order_result"]

    # ---------- note ----------
    def triggered_note_errors(self) -> list[str]:
        return [nid for nid, e in self.case["note_errors"].items() if e["trigger_topic"] in self.topics_asked]

    def sign_note(self, corrections: set[str] | None = None) -> None:
        self.note_corrections = set(corrections or ())
        self.note_signed = True
        self._log("sign_note", sorted(self.note_corrections))
        if self.node in ("ENCOUNTER", "NOTE"):
            self.node = "D1"

    def note_error_uncorrected(self, nid: str) -> bool:
        e = self.case["note_errors"][nid]
        return nid in self.triggered_note_errors() and e["correction_action"] not in self.note_corrections

    # ---------- assistant ----------
    def _vein_known(self) -> bool:
        return "vein_mapping" in self.orders

    def _condition_ok(self, cond: str | None) -> bool:
        if cond is None:
            return True
        return {
            "vein_status_unknown": not self._vein_known(),
            "vein_status_known": self._vein_known(),
            "n1_signed_uncorrected": self.note_signed and self.note_error_uncorrected("N1"),
            "creatinine_resulted": "creatinine" in self.orders,
        }[cond]

    def query_assistant(self, topic: str) -> dict | None:
        """Pick the spec'd output for a topic. Conditional outputs take priority.
        None = off-spec topic: model answers correctly from the chart at Moderate confidence."""
        cands = [(oid, o) for oid, o in self.case["assistant"].items() if o["kind"] == "topic" and o["topic"] == topic]
        cands.sort(key=lambda x: x[1].get("when") is None)  # conditional first
        for oid, o in cands:
            if self._condition_ok(o.get("when")):
                self.assistant_seen.append((oid, "query"))
                self._log("query_assistant", topic, oid)
                return {"id": oid, **o}
        self._log("query_assistant", topic, None)
        return None

    def _refresh_alerts(self) -> None:
        for oid, o in self.case["assistant"].items():
            if o["kind"] != "alert" or oid in self.alerts_shown:
                continue
            trig = o["appears_after"]
            if trig in self.orders or (trig == "d1" and any(n == "D1" for n, _ in self.actions)):
                self.alerts_shown.append(oid)
                self._log("alert_shown", oid)

    def open_alert(self, oid: str) -> dict:
        if oid not in self.alerts_shown:
            raise ValueError(f"alert {oid} not shown")
        self.alerts_opened.append(oid)
        self.assistant_seen.append((oid, "alert"))
        self._log("open_alert", oid)
        return {"id": oid, **self.case["assistant"][oid]}

    # ---------- decisions ----------
    def decide(self, actions: list[str]) -> dict:
        """Apply classifier output (ordered action ids) at the current node.
        Returns {'node': next_node, 'needs_followup': bool, 'results': {...}}."""
        node = self.node
        if node in ("ENCOUNTER", "NOTE"):
            raise ValueError("sign the note before the first decision")
        if node == TERMINAL:
            raise ValueError("case is over")
        results = {}
        for a in actions:
            self.actions.append((node, a))
            for test in ACTION_ORDERS.get(a, []):
                if node == "D3" and test == "cta_runoff" and "creatinine" not in self.orders:
                    self.flags.add("cta_without_creatinine")
                results[test] = self.order(test)
        self._log("decide", node, actions)
        s = set(actions)
        nxt, followup = getattr(self, f"_from_{node}")(s, actions, results)
        if not followup:
            self.node = nxt
        self._refresh_alerts()
        return {"node": self.node, "needs_followup": followup, "results": results}

    def _from_D1(self, s, actions, results):
        # Noninvasive studies obtained during the visit count as the vascular workup.
        did_noninvasive = bool({"abi_pvr", "toe_pressure"} & set(self.orders))
        if "enough_flow" in s or not (s & REVASC_WORKUP or did_noninvasive):
            self.flags.add("B1")
            return "B1", False
        return "D2", False

    def _from_D2(self, s, actions, results):
        if "perfusion_adequate" in s or "revasc_workup" not in s:
            self.flags.add("B1")
            return "B1", False
        return "D3", False

    def _from_B1(self, s, actions, results):
        self.flags.add("toe_lost")
        if "revasc_workup" in s:
            return "D3", False
        self.terminal_reason = "B1b"
        return TERMINAL, False

    def _from_D3(self, s, actions, results):
        if "bypass_without_mapping" in s and not self._vein_known():
            self.terminal_reason = "B2"
            return TERMINAL, False
        if "angiogram" not in self.orders:
            return "D3", True  # unclear: classifier/educator asks a follow-up
        first_angio = self.orders.index("angiogram")
        if "vein_mapping" not in self.orders[:first_angio]:
            if "vein_mapping" not in self.orders:
                return "D3b", False  # stop at the angiogram result: what next?
            self.flags.add("detour_second_angiogram")  # mapping planned after the angiogram
        return "D4", False

    def _from_D3b(self, s, actions, results):
        """Angiogram done before vein mapping: three-vessel tibial disease, vein status unknown."""
        if "bypass_without_mapping" in s:
            self.terminal_reason = "B2"
            return TERMINAL, False
        if "endo_tibial_before_mapping" in s:
            # Author: revascularized, but returns 3 months later with another wound; marked incorrect.
            self.flags.update({"revascularized", "endo_before_vein_mapping"})
            return "D5", False
        if "vein_mapping" in self.orders:
            self.flags.add("detour_second_angiogram")
            return "D4", False
        return "D3b", True

    def _from_D4(self, s, actions, results):
        if s & {"bypass_prosthetic", "bypass_cryo"}:
            self.terminal_reason = "B2"
            return TERMINAL, False
        if "endo_tibial" in s:
            self.flags.add("revascularized")
            return "D5", False
        return "D4", True

    def _from_D5(self, s, actions, results):
        return TERMINAL, False

    # ---------- outcome ----------
    def risk_factor_status(self) -> dict:
        status = {}
        for rf, spec in self.case["risk_factors"].items():
            st = "not addressed"
            for _, a in self.actions:
                if a in spec["managed"]:
                    st = "managed"
                elif a in spec["deferred"]:
                    st = "deferred"
            status[rf] = st
        return status

    def outcome(self) -> dict:
        if self.node != TERMINAL:
            raise ValueError("case not finished")
        rf = self.risk_factor_status()
        ok = {k: v == "managed" for k, v in rf.items()}
        events = []
        if "toe_lost" in self.flags:
            events.append("Second toe amputation (osteomyelitis).")
        if self.terminal_reason:
            events.append(self.case["terminal"][self.terminal_reason])
            major_amp = True
            healed = False
        else:
            # Missed smoking cessation impairs healing exactly like missed offloading (author, Dictation 15).
            wound_ok = ok["offloading"] and ok["smoking"]
            healed = ok["diabetes"] and wound_ok
            major_amp = not ok["diabetes"]
            delayed = "B1" in self.flags
            why = " and ".join(r for r, k in (("no offloading", "offloading"), ("continued smoking", "smoking")) if not ok[k])
            if not ok["diabetes"]:
                events.append("Revascularized with improved flow, but the wound did not heal with uncontrolled diabetes. Below-knee amputation.")
            elif not wound_ok and delayed:
                events.append(f"Revascularization was delayed and wound healing was impaired ({why}); it did not heal. Transmetatarsal amputation.")
            elif not wound_ok:
                if "Second toe amputation (osteomyelitis)." not in events:
                    events.append(f"Wound healing was impaired ({why}); the toe did not heal despite revascularization. Second toe amputation.")
            else:
                events.append("The wound healed.")
            if "endo_before_vein_mapping" in self.flags:
                events.append(self.case["events"]["endo_before_vein_mapping"])
        # Missed antiplatelet carries the same consequence as missed LDL management (author, Dictation 15).
        # After a major amputation the MI is reported once, by the postoperative rule below.
        mi_why = " and ".join(r for r, k in (("LDL not managed", "ldl"), ("antiplatelet not started", "antiplatelet")) if not ok[k])
        if mi_why and not major_amp:
            events.append(f"Myocardial infarction ({mi_why}).")
        died = False
        if major_amp:
            misses = (not ok["ldl"]) + (not ok["antiplatelet"])
            if misses == 2:
                died = True
                events.append("Postoperative myocardial infarction after amputation. He died.")
            elif misses == 1:
                events.append("Postoperative myocardial infarction after amputation. He survived.")
        return {"healed": healed, "major_amputation": major_amp, "died": died,
                "terminal_reason": self.terminal_reason, "risk_factors": rf,
                "flags": sorted(self.flags), "events": events}

    # ---------- calibration ----------
    def calibration(self) -> dict:
        acts = [a for _, a in self.actions]
        items = []
        seen = {oid for oid, _ in self.assistant_seen}
        for oid, o in self.case["assistant"].items():
            correct = o["correct"]
            if oid in seen:
                last = None
                for a in acts:
                    if a in o["adopt"]:
                        last = "adopt"
                    elif a in o["override"]:
                        last = "override"
                if correct == "low_value":
                    cell = "low-value output opened"
                elif last is None:
                    cell = "seen, no clear action"
                else:
                    cell = {(True, "adopt"): "appropriate reliance", (True, "override"): "reflexive dismissal",
                            (False, "adopt"): "overreliance", (False, "override"): "appropriate override"}[(correct, last)]
            elif oid in self.alerts_shown:
                cell = "alert not opened"
            else:
                cell = "not consulted"
            items.append({"id": oid, "correct": correct, "cell": cell})
        for nid in self.triggered_note_errors():
            cell = "overreliance" if self.note_error_uncorrected(nid) else "appropriate override"
            items.append({"id": nid, "correct": False, "cell": cell})
        counts = {}
        for it in items:
            counts[it["cell"]] = counts.get(it["cell"], 0) + 1
        return {"items": items, "counts": counts}

    def _log(self, *ev):
        self.log.append(ev)
