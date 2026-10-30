# CLTI-01 classifier check (Claude-drafted; labels approved by author Oct 30)

| # | Node | Resident says | Expected classification | What it tests |
|---|---|---|---|---|
| 1 | D1 | "Foot's warm, I think he has enough flow. Dressing changes and see him back." | Enough blood to heal -> B1 | Wrong path, casual phrasing |
| 2 | D1 | "Refer him to wound care and have his PCP handle the sugars and cholesterol." | Wound care center -> "not available"; risk factors per PCP (= not managed); no vascular workup ordered -> B1 (osteomyelitis branch) | Multi-decision + deferral |
| 3 | D2 | "ABI's 1.7, so inflow is fine. Ischemia isn't the problem here." | Accepts ABI as adequate perfusion -> B1 | Headline error adopted |
| 4 | D2 | "Ankles are noncompressible. Toe pressure 23, so he's ischemic. WIfI 1-3-1, needs a revasc workup." | Correct: recognizes noncompressible, I3, WIfI W1 I3 fI1, proceed | Correct, terse shorthand |
| 5 | D3 | "I wouldn't bother with an MRI, but let's get a CTA." | Orders CTA; does NOT order MRI; creatinine not checked (scored) | Negation |
| 6 | D3 | "Book him for an angiogram, we'll figure out vein later." | Angiogram before vein mapping -> detour | Detour path |
| 7 | D3 | "Check a creatinine, get bilateral vein mapping, then angio." | Creatinine, vein mapping, angiogram (correct order) | Sequence |
| 8 | D3 | "He's young, let's just take him for a fem-tibial bypass." | OR without vein mapping -> B2 | Wrong path |
| 9 | D4 | "Revascularize him and optimize everything." | Unclear -> follow-up ("Open or endo? What exactly?") | Vague answer, must not guess |
| 10 | D5 | "Atorvastatin 80, aspirin 81, refer to endo, and talk to him about quitting." | High-intensity statin, antiplatelet, endocrinology referral, smoking cessation. BP not addressed (scored) | Multi-decision, partial |
