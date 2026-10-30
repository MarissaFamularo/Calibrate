# Calibrate: design decisions (locked)

Decided with the author, Oct 28, 2026. Coding agents: these override README wherever they conflict.

## Core concept
- Resident works a synthetic vascular case. An AI clinical assistant is AVAILABLE, not pushed; using it is optional.
- The assistant is sometimes right and sometimes wrong (planted errors, defined in the case spec).
- An AI educator gives feedback (timing depends on mode).

## Modes
- **Practice:** educator feedback after each decision.
- **Assessment:** educator silent during the case; full debrief + calibration profile at the end.
- Same case engine; mode only changes when the educator speaks.

## Assistant access
- Free use in both modes (no commit-first step). Resident can query the assistant anytime.
- Planted errors are bound to TOPICS (what the resident asks about) and ALERTS, not fixed moments.
- **Alerts:** at 1–2 points per case the assistant has an unsolicited alert. The UI shows only that an alert exists (badge); content is revealed only if the resident clicks. Opening is itself a measured choice.
- Possible low-value alerts so that ignoring an alert is a judgment call, not always an error (case-writing decision).

## Measured behaviors
- Queried assistant (what about, adopted or not)
- Alert shown, not opened
- Alert opened → acted on / caught error / dismissed correct advice
- Calibration cells: appropriate reliance, overreliance, appropriate override, reflexive dismissal (+ "not consulted")

## Resident input
- Free text at each decision, with dictation option (Muse Spark Open audio input; early add-on after core loop).
- Two separate model jobs:
  1. **Classifier:** maps free text to the case-defined action options for that node, or "unclear" → attending-style follow-up question ("So what are you ordering?"). Never guesses. Drives scoring + branching.
  2. **Educator:** grades reasoning against the rubric.
- Validation set: author writes ~10 sample responses per node with labels; report classifier agreement.

## Case structure
- **Branching.** Wrong choices lead to a consequence node → recovery decision → reconverge onto main path (bounded tree).
- Author writes consequence FACTS; model renders the narrative.
- Limitation to note in README: residents on different paths meet different errors; profiles less comparable.

## Clinical data
- **Hybrid.** Basics given (vitals, exam, labs, ABI). Discriminating tests must be ordered in free text; results returned only for what was ordered.
- Every orderable test's result is defined in the case spec. The model NEVER invents a result.
- Tests the author lists as **not indicated** return "not indicated" + a reason (teaching point; logged as low-value ordering, not scored in v1).
- Any test not in the spec returns **"not available"** (default).

## Reports
- MVP: resident report (calibration profile + debrief).
- Faculty view = list of saved sessions, each opening the same resident report. No separate design, no logins in v1. Cohort analytics = future.

## Assistant presentation
- Chat sidebar the resident types/dictates into; alert badge lives on it.
- Confidence label on each answer, set per topic by the case spec (deliberately varied: some planted errors high-confidence, some correct answers hedged).
- Citations only where the author supplies them in the spec; the model never invents a citation. Misapplied-real-citation errors (e.g., BEST-CLI) are allowed by design.

## Educator
- Feedback covers BOTH clinical reasoning and AI-use behavior. An AI-use line is mandatory in every piece of feedback (what they verified, took on faith, alerts ignored).
- Tone: attending-style, brief, direct, no praise inflation.
- **Practice mode: Socratic.** After each decision the educator asks a probing question, resident replies, educator follows up. Cap at 2 exchanges, then the educator states the teaching point plainly.
- **Assessment mode: direct.** No questions; end-of-case debrief per decision + calibration profile.

## Interaction modality (patient, assistant, educator)
- All three are text conversations; resident can type OR dictate (Muse Spark Open audio input). One shared dictation component.
- Spoken model replies (TTS) for all three = late stretch goal, not core.

## Patient
- Interactive interview played by Muse, answering ONLY from a patient script in the case spec. Unscripted questions → plausible "not sure"/deflection; never invents symptoms or history.
- **Assistant is AMBIENT (Abridge-style, mirrors the tool residents use):** it reads the chart AND receives the actual transcript of the resident's patient interview.
- Asymmetry comes from: (1) what the resident never asked (neither knows); (2) exam findings the resident elicits that are never verbalized/documented; (3) ambient-specific planted errors.
- Ambient error types: attribution (patient said rest pain → summary says "denies rest pain"), omission (stopped aspirin dropped), smoothing (hedged statement rendered as fact). Spec defines the error against the real transcript; verifier confirms the planted distortion occurred and nothing else was distorted.

## AI-drafted note (review and sign)
- After the interview, the ambient assistant drafts the H&P summary from chart + transcript.
- Resident reviews, edits, signs. Planted note errors (attribution/omission/smoothing) scored as corrected vs. signed.
- The signed note becomes part of the chart; later assistant outputs read it, so uncorrected errors can propagate.

## Scope
- MVP: ONE fully branched case (CLTI, diabetic toe ulcer). Second case = stretch.
- Stretch order: dictation (early) → second case → images in case → case-authoring agent (Muse Code SDK).

## Infrastructure
- Runtime model: Muse Spark Open via Baseten (`meta-models/muse-spark-open-1026`); provider swappable in config.
- Built primarily with Claude Code (Muse Code not required; confirmed by organizers Oct 28).
- Synthetic data only; no PHI anywhere, including testing.

## Open questions
- (see conversation; resolved items get moved above)
