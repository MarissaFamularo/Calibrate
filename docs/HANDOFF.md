# Handoff (Sun Nov 1, 9:30 PM ET)

Submission due **Wed Nov 4, 9 PM ET** (CV platform: public repo + 3-min video link). Meta API credit claim due the same time. Tue Nov 3 = last full day for organizer help. No live deployment required (Modal cut).

## Read first
1. docs/DEMO_PLAN.md and docs/DEMO_SCRIPT.md (video plan, VO, exact resident inputs; visit-1 A/P approved by author)
2. docs/DESIGN_DECISIONS.md, cases/clti-01.md (sections 11-12 = playtest decisions)
3. README.md (rewritten Nov 1 to match the build)

## State
- App is feature-complete for the demo. 62 offline tests pass.
- Both demo runs verified live (`scripts/demo_rehearsal.py good|over`): good = wound healed, 5 appropriate override + 3 appropriate reliance; overreliant = toe amputation -> TMA -> MI, 6 overreliance.
- Unscripted sweep (`scripts/sweep.py terse|per_pcp|bypass|visit1_orders`): all four reach correct outcomes; no follow-up loops; no internal IDs in attending text.

## Built Nov 1
- Attending never shows internal IDs or "planted" (guard + regenerate + scrub; A1c exempt).
- Report: per-decision verdict from the attending in BOTH modes; "Overall" sticks to counts and named outputs.
- Faculty view: check two sessions -> "Compare 2 selected" (side-by-side outcomes + grids).
- Note clipboard: live "Your corrections to the AI draft" diff.
- Thinking indicators: typing bubbles (patient, assistant) + labeled status pill (top center).
- Architecture graphic: docs/architecture.html -> docs/img/architecture.png (1920x1080).
- Author playtest fixes: no "PVR waveforms provided"; "treat endovascularly" at workup = angiogram; follow-ups escalate instead of repeating; workup orders written in earlier notes carry to the workup step (in written order); revasc workup after the ABI alert = override, scored at visit 1 only.

## Next
1. Independent unscripted playtest (author or Astra). Collect anything that confuses or loops.
2. Author records VO + screen (Tue). Relaunch Start Calibrate first. Good run: ask "Should we go endovascular first?" BEFORE writing the visit-1 plan.
3. After recording: subtitle file timed to the VO; verify repo public while logged out; submit; claim credits.

## Open (author's call, not blocking)
- Should a direct "How do I interpret his ABI?" repeat the planted ABI error? (Currently answers correctly.)
- Exam maneuvers not in the case return "No finding recorded." Keep?
- Off-spec assistant answers adopted into the plan are not scored. Post-hackathon.

## Working notes for the agent
- Mac folder: ~/Desktop/CoworkProjects/Apps/Calibrate (device_bash: $HOME/mnt/Calibrate). Deps: `pip install --user -r requirements.txt pytest` in the device VM if missing.
- Push flow: commit on Mac -> `git format-patch -1 HEAD -o _to_delete` -> stage -> `git am` in cloud clone /home/claude/calibrate -> push -> Mac `git fetch && git rebase origin/main` (deletion permission needed for git lock files).
- Model calls cap at 180 s per device_bash call: nohup + poll for long runs.
- Author preferences: concise, one question at a time, defensible defaults; she writes clinical content.
