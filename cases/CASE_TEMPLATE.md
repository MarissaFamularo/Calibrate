# Case template

Fill in plain language. Claude converts it to the YAML spec. Leave anything blank you haven't decided.

## 1. Chart
What the resident AND the ambient assistant can see (referral, PMH/PSH, meds, allergies, vitals, labs, any given studies).

## 2. Exam
What the resident sees on "examining." The assistant knows these only if spoken aloud or written into the note.

## 3. Patient script
What the patient says if asked. Facts NOT in the chart go here. One row per topic.

| Topic | Patient says |
|---|---|
| | |

## 4. Orderable tests
| Test | Result |
|---|---|
| | |

- **Not indicated** (test + one-line reason):
- Everything else returns "not available."

## 5. AI-drafted note errors
Errors the ambient assistant plants in the H&P it drafts after the interview.

| ID | Type (attribution / omission / smoothing) | What the note gets wrong | Triggered only if patient says… |
|---|---|---|---|
| | | | |

## 6. Decision nodes
For each node:
- **What's happening / data revealed:**
- **Question to the resident:**
- **Correct action(s):**
- **Acceptable alternatives:**
- **Wrong action(s) → branch?** If yes: consequence facts (time passed, findings) + recovery decision + where it rejoins.
- **Assistant (if asked):** what it says · correct or planted error (type) · confidence (High / Moderate / Low) · citation (if any).
- **Rubric:** what a good rationale names.

## 7. Alerts (unsolicited, badge only until clicked)
| ID | When it appears | Content | Correct / planted error / low value | Confidence |
|---|---|---|---|---|
| | | | | |

## 8. Error ledger
Quick count of planted errors vs. correct outputs, for balance.
