# CLTI-01: case spec (sorted from author dictation; source of truth = clti-01_AUTHOR_NOTES.md)

Status: draft for author review. Items marked TBD = not yet supplied by author.

## 1. Chart (visible to resident AND assistant from start)
- 58M referred by PCP for a foot wound found by the PCP (patient hadn't noticed it).
- PMH: diabetes mellitus (A1c 11), not on insulin; hypertension.
- Meds (chart list): metformin; metoprolol (started 1 yr ago); statin (ordered).
- No antiplatelet ordered. Not seen by endocrinology (PCP trialing metformin alone).
- Lipid panel: not checked in the last 12 months.
- No prior vascular imaging.
- Vitals (triage): BP 140/70; all other vitals within normal limits.
- Allergies: NKDA.

## 2. Exam (revealed only for components the resident requests)
| Component | Finding |
|---|---|
| Wound | Tip of 2nd toe, round, ~1 cm, full thickness, slough at base, no bone |
| Periwound | 1 cm erythema |
| Foot temperature | Warm |
| Femoral pulses | Palpable |
| Popliteal pulses | Palpable |
| Pedal pulses | Not palpable |
| Monofilament | Neuropathy |
| Footwear | Regular sneaker |

## 3. Patient script (only if asked)
| Topic | Patient says |
|---|---|
| Wound awareness | Didn't notice it; PCP found it |
| Pain | No rest pain, no claudication |
| Work / footwear | Job requires a boot; wears it at work; boot sometimes gets wet |
| Statin | Has a statin prescription but doesn't take it |
| Smoking | Smokes 1 ppd x 30 years |
| Diabetes care | PCP trying metformin alone to see how he does; never seen endocrinology |

## 4. Orderable tests
| Test | Result |
|---|---|
| ABI / PVR (wound-side) | Ankle non-compressible, ABI 1.7 (numbers + waveforms) |
| Toe pressure / digit PVR | TP 23 mmHg, flattened digit waveforms on wound foot |
| Foot X-ray, visit 1 | No abnormality |
| Foot X-ray, 2-week return | Distal phalanx abnormality c/w osteomyelitis, isolated to the toe |
| Creatinine | 1.2 |
| CTA runoff | No significant aortoiliac disease; no fem-pop disease; calcific tibial disease, tibials not well seen |
| Vein mapping | GSV < 2 mm throughout, bilaterally |
| Angiogram | Three-vessel tibial disease |
| Lipid panel | LDL 110 |
| A1c | 11 (already in chart) |

- **Not indicated:** MRI foot at 2-week return (wound probes to bone; X-ray sufficient).
- **Not available (custom message):** wound care center referral -> "There is no wound care center; you manage the wound."
- Everything else returns "not available."

## 5. AI-drafted note errors
| ID | Type | What the note gets wrong | Triggered only if patient says | Downstream modifier if signed uncorrected |
|---|---|---|---|---|
| N1 | Attribution | Lists statin as active therapy | "I don't take the statin" | LDL |
| N2 | Omission | Social history omits smoking | Smokes 1 ppd x 30 yrs | Smoking |
| N3 | Smoothing | "Wears appropriate footwear" | Boot at work, sometimes wet | Offloading |

## 6. Decision nodes
### D1 Visit 1 plan
- Correct: ABI/PVR with toe pressures; baseline foot X-ray; offloading (surgical shoe); resident-managed wound care; start risk-factor workup and management.
- Wrong -> branch B1: "enough blood to heal" / wound care only with no vascular workup (incl. wound care referral + no workup).
- Wrong (modifier): "per PCP" for any risk factor.
### D2 Noninvasive results
- Correct: recognize non-compressible ankle vessels; ischemia by toe pressure; WIfI W1 I3 fI1; proceed to revascularization workup.
- Wrong -> branch B1: accept ABI 1.7 as adequate perfusion.
### D3 Imaging / anatomic workup
- Correct: CTA optional (must check creatinine first); vein mapping BEFORE angiogram.
- Detour (not a fail): angiogram before vein mapping -> mapping afterward shows inadequate vein -> second angiogram for treatment; rejoins at D4.
- Wrong -> branch B2: go to OR for bypass without vein mapping.
- BEST-CLI (assistant A3 cites it) supports endovascular only after vein mapping shows no adequate GSV; before vein status is known, surgery first is more appropriate on available data (Dictation 2).
### D4 Revascularization
- Findings: three-vessel tibial disease; no single-segment GSV.
- Correct: endovascular treatment of one tibial vessel (balloon angioplasty), supported by BEST-CLI given no adequate GSV.
### D5 Medical management (also scored throughout)
- Correct: high-intensity statin regardless of LDL level; LDL goal <70 or <55 by risk; antiplatelet therapy; smoking cessation offered; diabetes management + endocrinology referral; BP management; AHA guideline-concordant. Resident manages, does not defer to PCP. Assistant use for guideline lookup is expected and fine.

### Branches
- **B1 (from D1 or D2):** returns at 2 weeks; wound probes to bone. X-ray = correct (osteomyelitis distal phalanx); MRI = not indicated. Outcome: loses the toe; revascularization still required -> rejoins at D3.
- **B1b (from B1, terminal):** still no angiogram / revascularization workup at the 2-week visit -> returns 2 weeks later with gas gangrene of the foot -> guillotine amputation, then higher-level amputation. TERMINAL. Amputation modifiers (postoperative MI/death) apply.
- **B2 (from D3):** no decision offered. Narrative: you went to the OR, there was no adequate vein (< 2 mm), so PTFE or CryoVein was needed; no CryoVein in house, so PTFE was used -> graft infection, occlusion, explant -> below-knee amputation. TERMINAL (deliberate exception to rejoin rule); no endovascular bailout.

## 7. Assistant outputs and alerts
| ID | Topic / alert | Content | Correct? | Confidence | Citation |
|---|---|---|---|---|---|
| A1 | ALERT after ABI results | "ABI 1.7, perfusion adequate for healing" | Planted (headline) | High | - |
| A2 | WIfI | W1, fI1, ischemia I0 (from ankle pressure) | Planted | High | - |
| A3 | Revasc strategy, before vein status known | Endo first | Planted (misapplied citation) | High | BEST-CLI |
| A4 | Lipid goal | "LDL <100" | Planted | Moderate | - |
| A5 | Antiplatelet / BP / diabetes / smoking cessation | Guideline-concordant | Correct | High | AHA guidelines (2024 ACC/AHA lower extremity PAD guideline; author to confirm) |
| A6 | Contrast safety | Cr 1.2 acceptable for CTA | Correct | Hedged (Low/Moderate) | - |
| A7 | ALERT at visit 1 wrap-up | Influenza vaccine due | Low value | Moderate | - |

## 8. Outcome modifiers (applied at end; deterministic)
| Missed | Consequence |
|---|---|
| LDL / statin | Wound heals; MI |
| Diabetes (no A1c follow-up, no endo/management) | Revascularized but no healing -> below-knee amputation |
| Offloading | Timely revasc: toe amputation. Delayed revasc (B1): TMA. Diabetes also unmanaged: BKA |
| Smoking cessation | Same as missed offloading (impaired wound healing) |
| Antiplatelet | Same as missed LDL (MI) |
| "Per PCP" for a risk factor | Counts as not managed |
| Major amputation (BKA or higher) + LDL OR antiplatelet missed | Postoperative MI, survives  |
| Major amputation (BKA or higher) + LDL AND antiplatelet missed | Postoperative MI, death  |
- Best outcome: wound heals (at most toe amputation if B1 taken).

## 9. Error ledger
- Planted: 7 (N1-N3, A1-A4). Correct: A5 (multiple topics), A6. Low value: A7.

## 10. Open items
- Classifier check: ~10 tricky sample responses (negations, vague, multi-decision), written and labeled by Claude from this spec, run during build; author reviews only misreads.
