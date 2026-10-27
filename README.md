# Calibrate

**A simulation that teaches surgical residents when to trust an AI assistant and when to override it.**

Built for the Meta Global AI Developer Hackathon (Oct 27 – Nov 4, 2026), track: *Build for Your World*.

## The problem

Residents are starting to train alongside AI decision-support tools, but nobody teaches them how to *use* one. There are two ways to fail:

- **Overreliance (automation bias):** accepting a confident, wrong recommendation.
- **Reflexive dismissal (algorithm aversion):** rejecting a correct recommendation because it came from a machine.

Both are measurable, but neither gets taught. Residency programs have no standard way to practice or assess this skill.

## What Calibrate does

A resident works through a synthetic patient case. At set decision points, an AI assistant offers a recommendation. Some recommendations are sound and some contain a deliberately planted error. The resident accepts, questions, or overrides the recommendation and writes a short rationale. An AI educator then debriefs each decision. At the end, the resident gets a calibration profile: how often they caught real errors and how often they rejected good advice.

**This is not a clinical tool and does not give medical advice.** All patients are synthetic. The assistant's errors are designed teaching stimuli, defined in advance by a clinician-authored case specification. Nothing here is meant for real patient care.

## How it uses Meta's models

| Role | Model | What it does |
|---|---|---|
| Imperfect clinical assistant | Muse Spark | Renders each recommendation in natural clinical language from a case spec that fixes the ground truth and the planted error (if any) at that decision point |
| Error verifier | Muse Spark + deterministic checks | Confirms that each generated recommendation contains exactly the intended error and nothing unplanned before the resident sees it |
| Educator | Muse Spark | Grades the resident's free-text rationale against a case rubric and explains what they caught, missed, or wrongly rejected |
| *(stretch)* Spoken rationale | Muse Voice Transcribe | Lets residents talk through their reasoning the way they would on rounds |

**Why this split:** the case spec keeps the teaching content controlled and reproducible, and the model makes the assistant read like a real tool instead of a script. The verifier catches the main risk: a generated recommendation with an error nobody planted.

## Calibration metrics

Every assistant recommendation is either correct or incorrect, and every resident response either accepts or overrides it:

|  | Resident accepts | Resident overrides |
|---|---|---|
| **Assistant correct** | Appropriate reliance | Reflexive dismissal |
| **Assistant incorrect** | Overreliance | Appropriate override |

The session report summarizes these cells per resident, along with rationale quality from the educator's grading.

## MVP scope

- [ ] 3–5 synthetic vascular surgery cases, each with a spec defining the decision points, ground truth, and planted errors
- [ ] Assistant generation + verifier loop
- [ ] Resident accept / question / override capture with written rationale
- [ ] Educator debrief per decision
- [ ] Session calibration report

Out of scope for now: voice (stretch goal), longitudinal tracking across sessions, adaptive case difficulty.

## Built during the hackathon

All code in this repository was written between Oct 27 and Nov 4, 2026. Before the event, the only thing that existed was a one-paragraph concept README.

## Status

Pre-development. No working prototype yet. Educational effectiveness has not been studied.

## Author

Marissa Famularo, DO — vascular surgeon, Associate Program Director (Vascular Surgery Residency), and health data scientist.
