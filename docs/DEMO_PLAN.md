# Calibrate: demo plan (recorded video, 3:00)

Decided Nov 1. Submission needs: public repo + demo video link + team members. No live deployment required -> Modal deploy cut.
Track/theme: Build for Your World. Synthetic data only.

## Framing guardrails (rules compliance)
- Not "AI medical advice" and not an "AI for education chatbot": Calibrate is a simulation that MEASURES how residents rely on AI (calibration grid), with deterministic case truth. Say this explicitly in the video and README.
- Identify contributions: everything shown was built Oct 26 - Nov 4 (say so on screen + README "What we built" section).
- Tone: the assistant is a colleague to use well, not an error hunt.

## Script
0:00-0:25 Hook (author VO): two camps on AI (use it for everything / it hallucinates, never use it); no education for doctors in training on when and how to use AI to be efficient and safe while avoiding pitfalls; they need to calibrate trust and map the frontier of each tool. "That's Calibrate."
0:25-1:05 Encounter, good resident, practice mode: interview (patient: "I don't take the statin"); exam (pedal pulses not palpable); in-visit ABI 1.7 / TP 23; scribe drafts note listing statin as active (N1) -> resident corrects (visible) and signs.
1:05-1:40 A1 alert: red badge -> opened -> "ABI 1.7, perfusion adequate" (high confidence) -> resident overrides (non-compressible, TP 23, I3) -> attending drops: one Socratic question, answer, teaching point + AI-use line.
1:40-2:05 Montage (sped up, captioned): resident USES assistant for antiplatelet/BP/smoking (A5, correct) and adopts it; vein mapping before angio; recognizes misapplied BEST-CLI (A3); tibial angioplasty.
2:05-2:40 Faculty view: overreliant resident, same case: signed statin error + accepted ABI alert -> toe loss (B1) + MI. Two calibration grids side by side (appropriate reliance + override vs overreliance).
2:40-3:00 Under the hood: 6 model roles on Muse Spark Open (open weights), structured outputs, verifier loop, deterministic truth layer; built during the hackathon.

## Build list (driven by the script)
Must:
1. Two scripted runs (good, overreliant) with exact inputs; rehearse live; fix anything on those paths.
2. Visible note correction (diff/"corrected" marker).
3. Faculty view: two sessions side by side (or report that reads well on camera).
4. "Thinking..." indicator for clean edit cuts.
5. Architecture graphic; captions; README rewrite (incl. "What we built" + framing).
Nice: patient illustration showing toe wound.
Cut: dictation, streaming, Modal deploy, A1 direct-question issue.

## Author time
- Approve run scripts (~15 min), record VO + screen (Tue), submit (Wed).
