# CLTI-01 classifier check: live results (2026-10-30 15:57)

Model: `meta-models/muse-spark-open-1026`, reasoning_effort=medium, seed=1026, temperature=0.2, repeats=3.
**Agreement: 30/30** (exact match of status and action set; item 7 also order).
Latency per classification: median 2.4s, max 5.0s.

| # | Run | Node | Resident says | Expected | Got | Follow-up | Match |
|---|---|---|---|---|---|---|---|
| 1 | 1 | D1 | Foot's warm, I think he has enough flow. Dressing changes and see him back. | enough_flow, wound_care_self | enough_flow, wound_care_self |  | yes |
| 1 | 2 | D1 | Foot's warm, I think he has enough flow. Dressing changes and see him back. | enough_flow, wound_care_self | enough_flow, wound_care_self |  | yes |
| 1 | 3 | D1 | Foot's warm, I think he has enough flow. Dressing changes and see him back. | enough_flow, wound_care_self | enough_flow, wound_care_self |  | yes |
| 2 | 1 | D1 | Refer him to wound care and have his PCP handle the sugars and cholesterol. | wound_care_referral, diabetes_per_pcp, lipids_per_pcp | wound_care_referral, diabetes_per_pcp, lipids_per_pcp |  | yes |
| 2 | 2 | D1 | Refer him to wound care and have his PCP handle the sugars and cholesterol. | wound_care_referral, diabetes_per_pcp, lipids_per_pcp | wound_care_referral, diabetes_per_pcp, lipids_per_pcp |  | yes |
| 2 | 3 | D1 | Refer him to wound care and have his PCP handle the sugars and cholesterol. | wound_care_referral, diabetes_per_pcp, lipids_per_pcp | wound_care_referral, diabetes_per_pcp, lipids_per_pcp |  | yes |
| 3 | 1 | D2 | ABI's 1.7, so inflow is fine. Ischemia isn't the problem here. | perfusion_adequate | perfusion_adequate |  | yes |
| 3 | 2 | D2 | ABI's 1.7, so inflow is fine. Ischemia isn't the problem here. | perfusion_adequate | perfusion_adequate |  | yes |
| 3 | 3 | D2 | ABI's 1.7, so inflow is fine. Ischemia isn't the problem here. | perfusion_adequate | perfusion_adequate |  | yes |
| 4 | 1 | D2 | Ankles are noncompressible. Toe pressure 23, so he's ischemic. WIfI 1-3-1, needs a revasc workup. | noncompressible, ischemic_by_tp, wifi_correct, revasc_workup | noncompressible, ischemic_by_tp, wifi_correct, revasc_workup |  | yes |
| 4 | 2 | D2 | Ankles are noncompressible. Toe pressure 23, so he's ischemic. WIfI 1-3-1, needs a revasc workup. | noncompressible, ischemic_by_tp, wifi_correct, revasc_workup | noncompressible, ischemic_by_tp, wifi_correct, revasc_workup |  | yes |
| 4 | 3 | D2 | Ankles are noncompressible. Toe pressure 23, so he's ischemic. WIfI 1-3-1, needs a revasc workup. | noncompressible, ischemic_by_tp, wifi_correct, revasc_workup | noncompressible, ischemic_by_tp, wifi_correct, revasc_workup |  | yes |
| 5 | 1 | D3 | I wouldn't bother with an MRI, but let's get a CTA. | order_cta | order_cta |  | yes |
| 5 | 2 | D3 | I wouldn't bother with an MRI, but let's get a CTA. | order_cta | order_cta |  | yes |
| 5 | 3 | D3 | I wouldn't bother with an MRI, but let's get a CTA. | order_cta | order_cta |  | yes |
| 6 | 1 | D3 | Book him for an angiogram, we'll figure out vein later. | angio_before_mapping | angio_before_mapping |  | yes |
| 6 | 2 | D3 | Book him for an angiogram, we'll figure out vein later. | angio_before_mapping | angio_before_mapping |  | yes |
| 6 | 3 | D3 | Book him for an angiogram, we'll figure out vein later. | angio_before_mapping | angio_before_mapping |  | yes |
| 7 | 1 | D3 | Check a creatinine, get bilateral vein mapping, then angio. | order_creatinine, vein_mapping_first, order_angiogram | order_creatinine, vein_mapping_first, order_angiogram |  | yes |
| 7 | 2 | D3 | Check a creatinine, get bilateral vein mapping, then angio. | order_creatinine, vein_mapping_first, order_angiogram | order_creatinine, vein_mapping_first, order_angiogram |  | yes |
| 7 | 3 | D3 | Check a creatinine, get bilateral vein mapping, then angio. | order_creatinine, vein_mapping_first, order_angiogram | order_creatinine, vein_mapping_first, order_angiogram |  | yes |
| 8 | 1 | D3 | He's young, let's just take him for a fem-tibial bypass. | bypass_without_mapping | bypass_without_mapping |  | yes |
| 8 | 2 | D3 | He's young, let's just take him for a fem-tibial bypass. | bypass_without_mapping | bypass_without_mapping |  | yes |
| 8 | 3 | D3 | He's young, let's just take him for a fem-tibial bypass. | bypass_without_mapping | bypass_without_mapping |  | yes |
| 9 | 1 | D4 | Revascularize him and optimize everything. | unclear | unclear | You said revascularize - what specific revascularization are you planning, open bypass or endovascular? And what specifically do you mean by optimize everything? | yes |
| 9 | 2 | D4 | Revascularize him and optimize everything. | unclear | unclear | You said revascularize - how? Open bypass or endo tibial intervention? And what specifically are you optimizing? | yes |
| 9 | 3 | D4 | Revascularize him and optimize everything. | unclear | unclear | You said 'revascularize him' - how? Open bypass or endo tibial intervention? What exactly are you doing? | yes |
| 10 | 1 | D5 | Atorvastatin 80, aspirin 81, refer to endo, and talk to him about quitting. | statin_high_intensity, antiplatelet, diabetes_management, smoking_cessation | statin_high_intensity, antiplatelet, diabetes_management, smoking_cessation |  | yes |
| 10 | 2 | D5 | Atorvastatin 80, aspirin 81, refer to endo, and talk to him about quitting. | statin_high_intensity, antiplatelet, diabetes_management, smoking_cessation | statin_high_intensity, antiplatelet, diabetes_management, smoking_cessation |  | yes |
| 10 | 3 | D5 | Atorvastatin 80, aspirin 81, refer to endo, and talk to him about quitting. | statin_high_intensity, antiplatelet, diabetes_management, smoking_cessation | statin_high_intensity, antiplatelet, diabetes_management, smoking_cessation |  | yes |
