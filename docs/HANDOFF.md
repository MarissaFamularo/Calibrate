# Handoff (Fri Oct 30, afternoon ET)

## Read first, in order
1. docs/DESIGN_DECISIONS.md (locked design)
2. cases/clti-01.md (author-approved case; human-readable) and cases/clti-01.yaml (machine spec the engine reads)
3. docs/BUILD_PLAN.md (stack, components, schedule)
4. docs/BASETEN_NOTES.md (model API)
Author's raw words: cases/clti-01_AUTHOR_NOTES.md. Never add clinical facts the author didn't give; ask her.

## Done
- Case 1 fully specified and approved, including outcome rules.
- Engine (calibrate/engine.py). Fixed Oct 30 to match approved spec: B2 narrative = PTFE (no CryoVein in house, Dictation 15); missed smoking cessation impairs healing like missed offloading; missed antiplatelet -> MI like missed LDL; MI reported once after major amputation; lipid panel / A1c orderable from decisions.
- Model layer (Sat work, done early):
  - calibrate/config.py (model, seed 1026, per-role reasoning_effort, verifier toggles), calibrate/llm.py (Baseten client, strict json_schema, retries, truncation handling, per-call latency log; FakeLLM for tests).
  - calibrate/guards.py: deterministic checks on every output (no numbers or citations absent from the source) + generate/check/regenerate (max 2) / deterministic fallback.
  - calibrate/roles/: patient, scribe (+ note-edit judge), assistant (router, spec renderer, off-spec answerer), classifier (+ deterministic sequencing of vein-first vs angio-first; any bypass at D4 -> B2), educator (Socratic 2-exchange cap; assessment debrief; mandatory ai_use_line field).
  - calibrate/runtime.py: CaseRun orchestrator = the API the UI calls (interview, examine, order, draft_note, sign_note, ask_assistant, pending_alerts, open_alert, decide, educator_reply, report, save). AI-use facts for the educator are built deterministically from the engine log.
  - YAML additions (no new clinical facts): patient_topics, assistant_topics, action_labels, global_actions, classifier_actions, rubrics (from clti-01.md section 6), note_error_checks.
- Tests: 49 passing offline (python3 -m pytest -q). Live: classifier check 30/30 (10 items x 3 repeats; docs/classifier_check_results.md). Full live assessment session: 32 calls, ~70 s, calls 1-5 s each (scripts/smoke_live.py).
- Device VM now has openai, pyyaml, pytest installed (pip --user); build/test/run all on the Mac via device_bash.

## Known limitations / watch
- Classifier 30/30 is on the development set (prompt and glosses were written with these items in view). Need held-out phrasings from playtests.
- Note verifier is not airtight: one live draft added "for hyperlipidemia" (not in chart) and passed. Fallback note is deterministic and always correct.
- Educator occasionally over-applies the rubric (e.g., asks about creatinine before angiogram; rubric only requires it before CTA).
- Off-spec assistant answers are chart-grounded only; management questions outside spec topics get "not in the record"-style answers.

## UI (built Fri Oct 30 evening, ahead of plan)
- calibrate/server.py (FastAPI) + calibrate/web/ (index.html, style.css, app.js, patient.svg). Run: `uvicorn calibrate.server:app --port 8000`, open http://localhost:8000. `CALIBRATE_FAKE=1` = scripted fake model (calibrate/fake.py) for UI work without network.
- Design per DESIGN_DECISIONS "UI": patient scene + speech bubble (questions and exam), note clipboard (plans live in the note), assistant top-right (collapsible, red + badge on alerts), chart tabs, God panel for the educator, report, faculty list (#faculty).
- Runtime additions: interview() returns {reply, exam}; current_note(), submit_note(ap, history), state(); follow-ups amend the same signed note (Addendum). Engine: exam_after_b1 (wound probes to bone at the 2-week return, author's words).
- Tests: 52 (incl. tests/test_server.py API walks in both modes with the fake model).

## Next
- Live playtest by the author; A/P-style classifier items (plans are now note-length).
- Dictation (shared mic component), deploy to Modal.

## Working notes for the agent
- Project on her Mac: ~/Desktop/CoworkProjects/Apps/Calibrate (device_bash: $HOME/mnt/Apps/Calibrate).
- Live runs: python3 scripts/run_classifier_check.py [repeats]; python3 scripts/smoke_live.py [practice|assessment]. Never print keys.
- device_bash calls cap at 180 s: run long jobs with nohup and poll.
- GitHub: see status at end of this file.
- Author preferences: concise, one question at a time, proceed with defensible defaults, she writes clinical content (Claude may propose, she approves).

## GitHub status
- Pushed to MarissaFamularo/Calibrate main (Oct 30, commit 2fc04cb + this handoff update). Pushes go through a cloud clone (/home/claude/calibrate) with add_repo push access; copy changed files from the Mac with device_stage_files, commit, push.
- Her Mac clone has the same files but its git index is behind origin. To sync without touching files: `git fetch && git reset origin/main` (mixed reset, run on her Mac).
