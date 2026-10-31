# Handoff (Fri Oct 30, 8:30 PM ET)

Submission due Wed Nov 4, 9 PM ET. Core loop + UI are done and playable; we are about a day ahead of BUILD_PLAN.

## Read first
1. docs/DESIGN_DECISIONS.md (locked design; "UI" section added Oct 30 evening)
2. cases/clti-01.md (approved case; section 11 = tonight's author decisions) and cases/clti-01.yaml (what the engine reads)
3. docs/BUILD_PLAN.md, docs/BASETEN_NOTES.md
Author's raw words: cases/clti-01_AUTHOR_NOTES.md. Never add clinical facts the author didn't give; ask her.

## How to run (author)
- Finder: Desktop/CoworkProjects/Apps/Calibrate -> double-click **Start Calibrate.command** -> browser opens http://localhost:8000.
- After ANY code/case change: close the Terminal window and relaunch (the case loads at startup; refreshing is not enough).
- No-API mode: `"Start Calibrate.command" fake` (scripted stand-in model, placeholder educator text).

## What exists
- **Engine** (calibrate/engine.py): deterministic truth. Nodes D1, D2, B1, D3, D3b (angio-before-mapping stop), D4, D5; terminals B1b, B2; outcome modifiers per clti-01.md section 8; calibration cells.
- **Model layer** (Muse Spark Open via Baseten, strict JSON schemas, seed 1026): patient, scribe (+ note-correction judge), assistant (router, spec renderer, off-spec answerer), verifier, classifier, educator. Every output passes deterministic guards (no unsupported numbers/citations); regenerate, then deterministic fallback.
- **Runtime** (calibrate/runtime.py, CaseRun): the API the UI uses. Exam and in-visit tests (ABI/PVR, toe pressures) go through the encounter box; plans live in signed notes; follow-ups amend the same note; in-visit ABI merges D1+D2 into the visit-1 note.
- **UI** (calibrate/server.py + calibrate/web/): patient scene + speech bubble, note clipboard, assistant panel (top 40%, collapsible, red + badge on alerts, content hidden until opened), chart/results/notes tabs, "God" educator panel (drops from top), end report with calibration grid, faculty list (#faculty).
- **Tests:** 59 offline (`python3 -m pytest -q`), incl. API walks in both modes. Live checks tonight: classifier 30/30 on the 10-item set (dev set), D3b phrasings 4/4, merged visit-1 plans 2/2, patient 14/14 sensible.

## Changed tonight from playtest feedback
Start-page copy (author's wording); patient SP rules + reason for visit; care-gap chart notes hidden; assistant routing fixed (broad questions and test interpretation go to the general answerer) and general answers now give real recommendations (checked against the record); creatinine/contrast answer waits for a creatinine; educator uses only results the resident had seen, one issue per question; in-visit ABI; D3b stop; launcher; no-cache headers.

## Open questions for the author (one at a time)
1. Confirm the reason-for-visit line (clti-01.md section 11).
2. Should a direct question like "How do I interpret his ABI?" repeat the planted A1 error ("ABI 1.7 = adequate perfusion")? Right now it gets a correct general answer, which can undercut the A1 alert test.
3. Exam maneuvers not in the case (capillary refill, Doppler signals) return "No finding recorded for that exam in this case." Add findings, or keep?
4. Scoring: angio-first per the AI, then recovering with vein mapping counts as overreliance on A3 (recovery shows in clinical feedback only). Keep?
5. The assistant can read the hidden care-gap chart notes and will mention them if asked broadly. Intended?

## Known issues / watch
- Classifier accuracy is only measured on one-line answers; plans are now note-length. Write 10 A/P-style check items (author labels) and rerun scripts/run_classifier_check.py.
- Educator still occasionally bundles issues in a follow-up question.
- Latency: patient ~1-2 s, assistant 4-6 s (general answers ~6 s), note draft ~5-15 s, educator 4-8 s per turn. No streaming yet.
- Note verifier not airtight (one draft added an unsupported "for hyperlipidemia").
- Patient illustration is simple and doesn't show the wound.

## Next (suggested order)
1. Author playtest from the start, both modes; collect fixes.
2. A/P-style classifier check items.
3. Dictation (Muse audio input, one mic component for patient/assistant/educator).
4. Deploy to Modal so judges can try it (BUILD_PLAN Mon); fallback = local for the video.
5. README rewrite to match the design (currently stale: says 3-5 cases, accept/override buttons).
6. Demo script + 3-minute video (Tue). Demo beats: in-visit ABI -> A1 alert caught vs. missed; uncorrected statin note error -> MI.

## Working notes for the agent
- Mac folder: ~/Desktop/CoworkProjects/Apps/Calibrate (device_bash: $HOME/mnt/Apps/Calibrate). Python deps installed there with pip --user; the launcher uses its own .venv.
- Model calls work from device_bash (local .env). Never print keys. Calls cap at 180 s: use nohup + poll for long runs.
- Git: push from a cloud clone (/home/claude/calibrate) via add_repo push access (author approved Oct 30), then sync the Mac with `git pull` in device_bash (needs delete permission for git lock files; request it if denied).
- Session logs save to sessions/ (gitignored).
- Author preferences: concise, one question at a time, proceed with defensible defaults; she writes clinical content (Claude may propose, she approves). Framing: the assistant is a colleague to use, not an error hunt; "you alone are responsible for the final decisions."
