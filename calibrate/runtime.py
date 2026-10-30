"""CaseRun: one resident session. Engine owns truth; roles render language.

UI-facing calls: interview, examine, order, draft_note, sign_note, ask_assistant,
pending_alerts, open_alert, decide, educator_reply, report, save."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .config import ModelConfig
from .context import chart_text, results_text, transcript_text
from .engine import TERMINAL, Session
from .roles import assistant, classifier, educator, patient, scribe


class CaseRun:
    def __init__(self, case: dict, llm, mode: str = "practice", cfg: ModelConfig | None = None):
        assert mode in ("practice", "assessment")
        self.case, self.llm, self.mode = case, llm, mode
        self.cfg = cfg or ModelConfig()
        self.s = Session(case, mode=mode)
        self.transcript: list[tuple[str, str]] = []
        self.encounter: list[dict] = []          # what the UI shows in the speech bubble history
        self.signed_notes: list[dict] = []       # chart: every signed note
        self.followup: str | None = None         # attending follow-up awaiting an amended A/P
        self.assistant_chat: list[dict] = []
        self.results: dict[str, str] = {}
        self.note: dict | None = None
        self.signed_text: str | None = None
        self.note_corrected: dict[str, bool] = {}
        self.records: list[dict] = []
        self.pending: dict[str, list] = {}      # node -> follow-up dialog
        self.applied: dict[str, list] = {}      # node -> actions already applied this visit
        self.exchanges: list[tuple[str, str]] = []
        self._seg_start = 0
        self._reported_alerts: set[str] = set()
        self._note_reported = False
        self.started = time.time()

    # ---------- encounter ----------
    def interview(self, question: str) -> dict:
        """Encounter box: questions go to the patient; exam maneuvers return findings as narration.
        Returns {"reply", "exam": [{"component", "finding"}]}. Exam findings never enter the transcript
        (the ambient scribe hears the maneuver being announced, not the finding)."""
        out = patient.answer(self.llm, self.case, question, self.transcript, self.cfg.max_regenerations)
        for t in out["topics"]:
            self.s.ask_patient(t)
        exam = [{"component": c, "finding": self.examine(c)} for c in out["exam"]]
        if not out["topics"] and not exam:
            self.s._log("ask_patient_unscripted", question)
        self.transcript += [("Physician", question), ("Patient", out["reply"])]
        self.encounter.append({"physician": question, "patient": out["reply"], "exam": exam})
        return {"reply": out["reply"], "exam": exam}

    def examine(self, component: str) -> str:
        return self.s.examine(component) or "Not available."

    def order(self, test: str) -> str:
        r = self.s.order(test)
        self.results[test] = r
        return r

    # ---------- note ----------
    def draft_note(self) -> str:
        triggered = self.s.triggered_note_errors()
        d = scribe.draft(self.llm, self.case, self.transcript, triggered, self.s.topics_asked,
                         verify_with_model=self.cfg.verify_scribe_with_model, max_regenerations=self.cfg.max_regenerations)
        self.note = {**d, "triggered": triggered}
        return d["text"]

    def sign_note(self, edited_text: str) -> None:
        if self.note is None:
            self.draft_note()
        trig = self.note["triggered"]
        self.note_corrected = scribe.judge_corrections(self.llm, self.case, self.note["text"], edited_text, trig) if trig else {}
        fixes = {self.case["note_errors"][n]["correction_action"] for n, ok in self.note_corrected.items() if ok}
        self.s.sign_note(fixes)
        self.signed_text = edited_text

    # ---------- assistant ----------
    def _record(self) -> str:
        conv = f"SIGNED NOTE:\n{self.signed_text}" if self.signed_text else f"INTERVIEW TRANSCRIPT:\n{transcript_text(self.transcript)}"
        return f"CHART:\n{chart_text(self.case)}\n\n{conv}\n\nRESULTED TESTS:\n{results_text(self.case, self.s.orders, self.results)}"

    def ask_assistant(self, question: str) -> dict:
        topic = assistant.route(self.llm, self.case, question)
        spec = self.s.query_assistant(topic)  # None for "other" or no matching spec output
        if spec:
            r = assistant.render_spec(self.llm, spec, question, verify_with_model=self.cfg.verify_assistant_with_model,
                                      max_regenerations=self.cfg.max_regenerations)
            msg = {"id": spec["id"], "topic": topic, "text": r["text"], "confidence": spec["confidence"],
                   "citation": spec.get("citation"), "info": r["info"]}
        else:
            r = assistant.answer_offspec(self.llm, question, self._record(), self.cfg.max_regenerations)
            msg = {"id": None, "topic": topic, "text": r["text"], "confidence": assistant.OFFSPEC_CONFIDENCE,
                   "citation": None, "info": r["info"]}
        self.assistant_chat.append({"question": question, **msg})
        return msg

    def pending_alerts(self) -> list[str]:
        """IDs of alerts that exist but are unopened. The UI shows a badge only."""
        return [a for a in self.s.alerts_shown if a not in self.s.alerts_opened]

    def open_alert(self, oid: str) -> dict:
        spec = self.s.open_alert(oid)
        r = assistant.render_spec(self.llm, spec, None, verify_with_model=self.cfg.verify_assistant_with_model,
                                  max_regenerations=self.cfg.max_regenerations)
        msg = {"id": oid, "alert": True, "text": r["text"], "confidence": spec["confidence"],
               "citation": spec.get("citation"), "info": r["info"]}
        self.assistant_chat.append(msg)
        return msg

    # ---------- decisions ----------
    def decide(self, text: str) -> dict:
        node = self.s.node
        if node in ("ENCOUNTER", "NOTE"):
            raise ValueError("sign the note before the first decision")
        if node == TERMINAL:
            raise ValueError("case is over")
        dialog = self.pending.get(node, [])
        c = classifier.classify(self.llm, self.case, node, text, dialog)
        if c["status"] == "unclear":
            self.pending[node] = dialog + [("Resident", text), ("Attending", c["followup"])]
            return {"node": node, "followup": c["followup"]}
        acts = classifier.to_engine_actions(node, c["actions"], self.s.orders)
        acts = [a for a in acts if a not in self.applied.get(node, [])]
        pre_log, pre_alerts = len(self.s.log), list(self.s.alerts_shown)
        r = self.s.decide(acts)
        self.results.update(r["results"])
        self.applied.setdefault(node, []).extend(acts)
        texts = [t for w, t in dialog if w == "Resident"] + [text]
        if r["needs_followup"]:
            q = classifier.FOLLOWUPS.get(node, "What else?")
            self.pending[node] = dialog + [("Resident", text), ("Attending", q)]
            return {"node": node, "followup": q, "results": r["results"]}
        self.pending.pop(node, None)
        all_acts = self.applied.pop(node)
        rec = {"node": node, "text": " / ".join(texts), "actions": all_acts,
               "action_labels": [self.case["action_labels"].get(a, a) for a in all_acts],
               "results": {k: self.results[k] for k in self._orders_since(pre_log, include_all=True)} | r["results"],
               "consequence": self._consequence(node),
               "ai_facts": self._ai_facts(pre_log, pre_alerts, all_acts)}
        self.records.append(rec)
        self._seg_start = len(self.s.log)
        out = {"node": self.s.node, "results": r["results"], "consequence": rec["consequence"],
               "next_prompt": self.case["nodes"].get(self.s.node, {}).get("prompt")}
        if self.mode == "practice":
            self.exchanges = []
            turn = self._educator_turn()
            out["educator"] = turn
        return out

    def educator_reply(self, text: str) -> dict:
        """Practice mode: resident answers the educator's question."""
        if self.mode != "practice" or not self.records:
            raise ValueError("no active educator exchange")
        if self.exchanges and self.exchanges[-1][0] == "Educator(teaching_point)":
            raise ValueError("exchange finished; make the next decision")
        self.exchanges.append(("Resident", text))
        return self._educator_turn()

    def _educator_turn(self) -> dict:
        rec = self.records[-1]
        ex = [("Educator" if w.startswith("Educator") else w, t) for w, t in self.exchanges]
        d = {"text": rec["text"], "actions": rec["action_labels"], "results": rec["results"], "consequence": rec["consequence"]}
        t = educator.socratic_turn(self.llm, self.case, rec["node"], d, rec["ai_facts"], ex)
        self.exchanges.append((f"Educator({t['kind']})", t["message"]))
        rec.setdefault("educator", []).append({k: t[k] for k in ("kind", "message", "ai_use_line")})
        return t

    # ---------- notes (plans live in the note) ----------
    def current_note(self) -> dict | None:
        """The note the resident must write/sign now, or None (interview not finished / case over)."""
        node = self.s.node
        if node == TERMINAL or (node == "ENCOUNTER" and self.note is None):
            return None
        key = "D1" if node in ("ENCOUNTER", "NOTE") else node
        hdr = []
        if key == "D1":
            hist, editable = self.signed_text or self.note["text"], not self.s.note_signed
        else:
            hist, editable = None, False
            seen = {o for n in self.signed_notes for o in n.get("results", {})}
            hdr = [{"test": o, "result": self.results[o]} for o in dict.fromkeys(self.s.orders)
                   if o in self.results and o not in seen]
        return {"node": key, "title": self.case["notes"].get(key, key), "prompt": self.case["nodes"][key]["prompt"],
                "history": hist, "history_editable": editable, "new_results": hdr, "followup": self.followup}

    def submit_note(self, ap: str, history: str | None = None) -> dict:
        """Sign the current note. Visit 1: `history` is the resident-edited AI draft (judged for
        corrections) and is locked at first signature. The A/P goes to the classifier."""
        cur = self.current_note()
        if cur is None:
            raise ValueError("no note to sign")
        if self.educator_open():
            raise ValueError("finish with the educator first")
        if not self.s.note_signed:
            self.sign_note(history if history is not None else self.note["text"])
        shown = {x["test"]: x["result"] for x in cur["new_results"]}  # results this note was written against
        r = self.decide(ap)
        self.followup = r.get("followup")
        status = "needs follow-up" if self.followup else "signed"
        prev = self.signed_notes[-1] if self.signed_notes else None
        if prev and prev["node"] == cur["node"] and prev["status"] == "needs follow-up":
            prev["ap"] += f"\nAddendum: {ap}"  # amended after the attending's follow-up
            prev["status"] = status
        else:
            self.signed_notes.append({"node": cur["node"], "title": cur["title"],
                                      "history": self.signed_text if cur["node"] == "D1" else None, "ap": ap,
                                      "results": shown, "status": status})
        return r

    def educator_open(self) -> bool:
        return (self.mode == "practice" and bool(self.exchanges)
                and not self.exchanges[-1][0].endswith("(teaching_point)"))

    def state(self) -> dict:
        node = self.s.node
        phase = ("done" if node == TERMINAL else "interview" if self.note is None
                 else "educator" if self.educator_open() else "note")
        return {"mode": self.mode, "node": node, "phase": phase, "case_title": self.case["title"],
                "chart": self.case["chart"], "results": [{"test": o, "result": self.results[o]} for o in dict.fromkeys(self.s.orders) if o in self.results],
                "encounter": self.encounter, "signed_notes": self.signed_notes, "note": self.current_note(),
                "alerts_pending": self.pending_alerts(), "assistant_chat": [{k: v for k, v in m.items() if k != "info"} for m in self.assistant_chat],
                "educator": (self.records[-1].get("educator") if self.records and self.mode == "practice" else None),
                "educator_node": self.records[-1]["node"] if self.records else None,
                "exchanges": [{"who": "educator" if w.startswith("Educator") else "resident", "text": t,
                               "kind": w[9:-1] if w.startswith("Educator(") else None} for w, t in self.exchanges]
                if self.mode == "practice" else []}

    # ---------- report ----------
    def report(self) -> dict:
        if self.s.node != TERMINAL:
            raise ValueError("case not finished")
        if getattr(self, "_report", None) is not None:
            return self._report
        outcome, cal = self.s.outcome(), self.s.calibration()
        rep = {"mode": self.mode, "outcome": outcome, "calibration": cal, "decisions": self.records}
        if self.mode == "assessment":
            decs = [{"node": r["node"], "text": r["text"], "actions": r["action_labels"], "results": r["results"],
                     "consequence": r["consequence"], "ai_facts": r["ai_facts"]} for r in self.records]
            rep["debrief"] = educator.debrief(self.llm, self.case, decs, cal, outcome)
        self._report = rep
        return rep

    def save(self, folder: str | Path = "sessions") -> Path:
        Path(folder).mkdir(exist_ok=True)
        p = Path(folder) / f"{self.case['id']}_{self.mode}_{int(self.started)}.json"
        data = {"case": self.case["id"], "mode": self.mode, "started": self.started, "transcript": self.transcript,
                "note": self.note, "signed_note": self.signed_text, "note_corrected": self.note_corrected,
                "assistant_chat": self.assistant_chat, "records": self.records,
                "engine_log": [list(e) for e in self.s.log],
                "report": self.report() if self.s.node == TERMINAL else None,
                "model_calls": getattr(self.llm, "calls", [])}
        p.write_text(json.dumps(data, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o)))
        return p

    # ---------- deterministic facts for the educator ----------
    def _orders_since(self, start: int, include_all=False) -> list[str]:
        return [e[1] for e in self.s.log[self._seg_start:] if e[0] == "order" and e[1] in self.results]

    def _consequence(self, node: str) -> str | None:
        nxt = self.s.node
        if nxt == TERMINAL:
            return self.case["terminal"].get(self.s.terminal_reason) if self.s.terminal_reason else "Case complete."
        if nxt == "B1":
            return self.case["nodes"]["B1"]["prompt"]
        if node == "D3" and "detour_second_angiogram" in self.s.flags:
            return "Angiogram came before vein mapping; mapping afterward shows no adequate vein, so a second angiogram is needed for treatment."
        return None

    def _ai_facts(self, pre_log: int, pre_alerts: list[str], acts: list[str]) -> list[str]:
        A = self.case["assistant"]
        label = {True: "correct", False: "PLANTED ERROR", "low_value": "low value"}
        facts = []
        if self.s.note_signed and not self._note_reported and self.note:
            self._note_reported = True
            for n in self.note["triggered"]:
                e = self.case["note_errors"][n]
                facts.append(f"AI-drafted note error {n} ({e['type']}: {e['error']}) was "
                             + ("corrected before signing." if self.note_corrected.get(n) else "signed uncorrected."))
        seen = []
        for ev in self.s.log[self._seg_start:pre_log]:
            if ev[0] == "query_assistant":
                if ev[2]:
                    o = A[ev[2]]
                    facts.append(f"Asked the assistant about {ev[1]}; it said \"{o['content']}\" "
                                 f"({o['confidence']} confidence, {label[o['correct']]}).")
                    seen.append(ev[2])
                else:
                    facts.append("Asked the assistant an off-spec question (answered from the chart).")
            elif ev[0] == "open_alert":
                o = A[ev[1]]
                facts.append(f"Opened alert {ev[1]}: \"{o['content']}\" ({label[o['correct']]}).")
                seen.append(ev[1])
        for oid in dict.fromkeys(seen):
            o = A[oid]
            if o["correct"] == "low_value":
                continue
            if set(acts) & set(o["adopt"]):
                facts.append(f"Decision followed {oid}.")
            elif set(acts) & set(o["override"]):
                facts.append(f"Decision went against {oid}.")
        for oid in pre_alerts:
            if oid not in self.s.alerts_opened and oid not in self._reported_alerts:
                self._reported_alerts.add(oid)
                o = A[oid]
                facts.append(f"Alert {oid} was available but not opened (it said \"{o['content']}\", {label[o['correct']]}).")
        if not facts:
            facts.append("Did not consult the AI assistant at this decision.")
        return facts
