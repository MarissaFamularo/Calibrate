# Calibrate: build plan

Written Oct 30, 2026. Due Wed Nov 4, 9 PM ET (Tue Nov 3 = last full day). Authority order: DESIGN_DECISIONS.md > cases/clti-01.md > this file > README.

## Principle
The model renders language; the code owns truth. Case facts, test results, branching, scoring, and outcomes are deterministic from the case spec. Muse never invents a result, a citation, or an outcome.

## Stack
- **Backend:** Python 3.12, FastAPI. Case spec as YAML (`cases/clti-01.yaml`, converted from `clti-01.md`).
- **Frontend:** single-page vanilla HTML/JS/CSS served by FastAPI (no build step).
- **Model:** Muse Spark Open via Baseten, OpenAI SDK, `meta-models/muse-spark-open-1026`, JSON-schema structured outputs, fixed seed for demo runs. Provider swappable in config.
- **Storage:** one JSON event log per session (`sessions/`), gitignored. SQLite only if needed.
- **Deploy:** Modal (FastAPI on a web endpoint; we have credits). Fallback: run locally for the video.

## Components
| Component | Deterministic or model | Notes |
|---|---|---|
| Case engine (state machine) | Deterministic | Nodes D1-D5, branches B1/B1b/B2, detour, terminal outcomes |
| Test/order resolver | Deterministic | Spec result / "not indicated" + reason / "not available" (incl. wound care center message) |
| Exam resolver | Deterministic | Only requested components returned |
| Outcome modifiers | Deterministic | LDL, diabetes, offloading, smoking, antiplatelet, per-PCP, amputation MI/death rules |
| Calibration scorer | Deterministic | Logs every assistant query/alert; 4 cells + "not consulted" |
| Patient | Muse | Answers only from patient script; unscripted -> deflect |
| Ambient scribe (note draft) | Muse + verifier | Drafts H&P from chart + transcript; inserts N1-N3 only if trigger fact was said |
| Assistant | Muse + verifier | Renders spec'd content per topic/alert with spec'd confidence; off-spec topics answered correctly from chart, moderate confidence |
| Verifier | Muse + string checks | Confirms planted error present, nothing else distorted; regenerate on fail (max 2), then fall back to spec text verbatim |
| Classifier | Muse | Free text -> node action options or "unclear" -> attending follow-up; never guesses |
| Educator | Muse | Practice: Socratic, 2-exchange cap. Assessment: end debrief. Mandatory AI-use line |
| Dictation | Muse Spark Open audio input | Shared mic component for all three conversations |

## Screens
1. **Encounter:** chart panel (always visible), patient chat, exam requests, orders + results panel.
2. **Assistant sidebar:** chat, confidence label per answer, alert badge (content hidden until clicked).
3. **Note review:** AI-drafted H&P, editable, Sign button.
4. **Decision box** at each node (free text + mic). Practice mode shows educator after each.
5. **Report:** outcome narrative, calibration 2x2, per-decision debrief, modifiers hit.
6. **Faculty view:** list of saved sessions -> same report.

## Schedule
| Day | Build | Author time |
|---|---|---|
| Fri Oct 30 | Case YAML; engine + resolvers + modifiers + scorer with a stub model; unit tests walking every path (ideal, detour, B1, B1b, B2) | None |
| Sat Oct 31 | Muse client; patient, scribe, assistant, verifier, classifier, educator prompts; run the 10-item classifier check | Review classifier misreads only |
| Sun Nov 1 | UI screens 1-4; practice/assessment toggle; end-to-end playable | 30 min playtest |
| Mon Nov 2 | Report + faculty list; dictation; deploy to Modal | 30 min playtest |
| Tue Nov 3 | Fixes; README rewrite to match design; demo script; latency tuning | Record 3-min video |
| Wed Nov 4 | Buffer; claim Meta credits; verify repo public logged-out; submit by 9 PM | Submit |

## Judging alignment
- **Meta tooling (25%):** six model roles on open weights, structured outputs, audio input, verifier loop ("verifiable agents"). Eligible for Best Open Weights ($10K) and Best Agentic Use-Case ($5K).
- **Impact (30%):** first tool to train and measure AI calibration in residents; mirrors the ambient tool residents already use.
- **Demo (25%):** show the note-error carry-forward (unsigned-corrected statin -> MI) and the ABI alert catch vs. miss.
- **Depth (20%):** deterministic truth layer, verifier, classifier accuracy number, path tests.

## Risks
- **Latency** (reasoning model): low `reasoning_effort` for patient/scribe; stream where possible.
- **Patient/scribe drift:** verifier + fall back to spec text.
- **Classifier misreads:** 10-item check; "unclear" follow-up instead of guessing.
- **Scope:** dictation and deploy are cuttable; core loop + report are not.
- **Public repo exposes the answer key** (planted errors). Acceptable for the hackathon; real use needs private case specs.

## README must be updated (currently stale)
3-5 cases -> 1 branched case; accept/override buttons -> free text + classifier; add ambient scribe, note signing, alerts, modes, outcome modifiers.
