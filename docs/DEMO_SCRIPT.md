# Calibrate demo script v1 (Nov 1) -- draft, author to approve VO and resident inputs

| Time | Screen | Voiceover |
|---|---|---|
| 0:00-0:25 | Title card -> start page | Ask around about AI in medicine and you'll hear two camps. It's great, use it for everything. It's dangerous, it hallucinates, never use it. Meanwhile, there's no education built for doctors in training on when and how to use AI: to be efficient and safe while avoiding the pitfalls. They need to learn to calibrate their trust and map the frontier of each tool. That's Calibrate. |
| 0:25-0:32 | Flash: calibration grid from end report | Calibrate is a simulation that measures how residents rely on AI: when they trust it, when they override it, and whether they were right. |
| 0:32-1:00 | Patient scene. Typed: "What brings you in today?" / "Are you taking all your medications?" / "Do you smoke?" / "Checking his pedal pulses." / "Getting an ABI and toe pressures now." | A synthetic patient, played by Muse Spark. Every exam finding and test result comes from the case spec; the model never invents one. Like the ambient scribes residents already use, the assistant hears the whole visit. |
| 1:00-1:15 | Assistant panel turns red -> click -> "ABI 1.7, perfusion adequate for healing. Confidence: high." | An alert. High confidence, and wrong. The ankle vessels are non-compressible; a toe pressure of 23 says this foot is ischemic. |
| 1:15-1:40 | AI-drafted note; highlight "statin: active" -> resident edits; adds smoking; types A/P; Sign | The assistant drafts the note, and lists the statin as active. He just said he doesn't take it. The resident fixes it before signing; an error signed into the chart follows the patient. |
| 1:40-1:55 | Attending panel drops: one question, short answer, teaching point + AI-use line | In practice mode, the attending weighs in on the reasoning and on the AI use: what you verified, and what you took on faith. |
| 1:55-2:15 | Sped-up montage, captions: "Asks assistant: antiplatelet, BP, smoking -> correct, adopted" / "Vein mapping before angiogram" / "Assistant cites BEST-CLI for endo-first -> misapplied before vein status known" / "No usable vein -> tibial angioplasty" | Using it well cuts both ways. Its antiplatelet and blood pressure guidance is right, and she takes it. Its endovascular-first advice cites a real trial, misapplied. |
| 2:15-2:42 | Faculty view -> two reports side by side | Same case, another resident. Signed the note as drafted, so no one started a statin or addressed his smoking. Trusted the alert. Transmetatarsal amputation, then an MI. Faculty see exactly where trust went wrong, and where it went right. |
| 2:42-3:00 | Architecture graphic | Six roles on Muse Spark Open: patient, scribe, assistant, verifier, classifier, attending. Structured outputs, a verifier on every output, and a deterministic case engine that owns the truth. Synthetic patients only. Built during this hackathon. |

## Resident inputs
Good run, visit-1 A/P (draft, author to approve):
"58M DM (A1c 11), HTN, 1 ppd smoker with full-thickness 2nd toe ulcer. Non-compressible ankle vessels; ABI 1.7 not reliable. TP 23 with flattened digit waveforms = ischemia. WIfI W1 I3 fI1, CLTI. Plan: surgical shoe offloading; local wound care, I will manage; foot X-ray; revascularization workup with vein mapping; start high-intensity statin, aspirin; smoking cessation counseling; endocrinology referral and diabetes management; BP management."
Note corrections: statin -> "prescribed, not taking"; add "smokes 1 ppd x 30 years"; footwear -> "work boot, sometimes wet."

Overreliant run: same interview; opens alert, writes "ABI 1.7, adequate perfusion. Wound care and surgical shoe, follow up 2 weeks."; signs note unedited. 2-week: X-ray, then revasc workup -> rejoins.

## To verify in rehearsal
- Uncorrected N1 alone triggers the LDL/MI modifier even if a statin is ordered later (check engine).
- Overreliant path ends: TMA + MI (author chose option A, Nov 1): N1+N2 uncorrected -> no statin, no cessation; accepts A1 -> B1.
