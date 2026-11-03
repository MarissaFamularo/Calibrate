"""Record the demo's screen footage from the live app (good run + faculty compare).
Needs the server running on :8000. Writes video/raw_good.webm, video/raw_faculty.webm, video/beats.json.
Usage: python3 scripts/record_demo.py good|faculty"""
import json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("video"); OUT.mkdir(exist_ok=True)
W, H = 1920, 1080
URL = "http://localhost:8000"
INTERVIEW = ["What brings you in today?", "Are you taking all your medications?", "Do you smoke?",
             "What kind of shoes do you wear at work?", "Checking his pedal pulses.", "Getting an ABI and toe pressures now."]
ASK = ["Should we go endovascular first for him?", "What antiplatelet should he be on?",
       "How should I manage his blood pressure?", "How should I help him quit smoking?"]
AP = {
    "D1": "58M DM (A1c 11), HTN, 1 ppd smoker with full-thickness 2nd toe ulcer. Non-compressible ankle vessels; ABI 1.7 not reliable. TP 23 with flattened digit waveforms = ischemia. WIfI W1 I3 fI1, CLTI. Plan: surgical shoe offloading; local wound care, I will manage; foot X-ray; revascularization workup with vein mapping; start high-intensity statin, aspirin; smoking cessation counseling; endocrinology referral and diabetes management; BP management.",
    "D3": "Check creatinine before any contrast. Angiogram after vein mapping. CTA runoff if creatinine allows.",
    "D4": "No adequate GSV. Angiogram with endovascular treatment of one tibial vessel, balloon angioplasty.",
    "D5": "Atorvastatin 80 mg, LDL goal <55. Aspirin 81 mg. Smoking cessation counseling and nicotine replacement. Endocrinology referral and diabetes management, I will follow A1c. BP management. Continue surgical shoe offloading and wound care.",
}
REPLY = {
    "D1": "The ankle vessels are non-compressible, so the ABI of 1.7 is falsely high. The toe pressure of 23 means he's ischemic and needs a revascularization workup.",
    "D3": "Vein mapping tells me whether he has a usable vein for bypass, and that decides open versus endovascular.",
    "D4": "Mapping showed no usable saphenous vein, so bypass isn't a good option and angioplasty is.",
    "D5": "He has CLTI and diabetes, so he's at very high risk. High-intensity statin with LDL under 55.",
}
FIX = [("statin", "statin (prescribed, NOT taking)"),
       ("Social history:", "Social history: Smokes 1 ppd x 30 years. Work boot, sometimes wet. WAS:")]

CLIPS = {"shoe": Path("video/src/dict_shoe.wav"), "abi": Path("video/src/dict_abi.wav")}
# Virtual microphone for the recording: getUserMedia returns a stream that plays the author's recorded clip,
# so the app's real dictation path (browser WAV -> /api/dictate -> Muse Spark Open) runs on her actual voice.
VMIC = """
window.__clip = null;
navigator.mediaDevices.getUserMedia = async () => {
  const ctx = new AudioContext(); const resp = await fetch(window.__clip);
  const buf = await ctx.decodeAudioData(await resp.arrayBuffer());
  const src = ctx.createBufferSource(); src.buffer = buf; const dest = ctx.createMediaStreamDestination();
  src.connect(dest); src.start(); return dest.stream;
};"""

def dictate(page, target, clip):
    page.evaluate(f"window.__clip = '/__clips/{clip}.wav'")
    page.click(f'button.mic[data-target="{target}"]')
    import wave
    with wave.open(str(CLIPS[clip])) as w: dur = w.getnframes() / w.getframerate()
    page.wait_for_timeout(int(dur * 1000) + 700)
    page.click(f'button.mic[data-target="{target}"]'); idle(page); page.wait_for_timeout(1500)

T0 = None
beats = []
def beat(name):
    beats.append({"beat": name, "t": round(time.time() - T0, 2)}); print(f"{beats[-1]['t']:7.1f}s  {name}", flush=True)

def idle(page, timeout=180_000):
    page.wait_for_timeout(300)
    page.wait_for_function("() => document.getElementById('busy').hidden", timeout=timeout)

def type_in(page, sel, text, delay=28):
    page.click(sel); page.keyboard.type(text, delay=delay)

def edit_line(page, needle, new):
    """Select the whole line containing `needle` in the history textarea and retype it (live diff updates)."""
    ok = page.evaluate("""([needle]) => { const t = document.getElementById('note-history'); const v = t.value;
        const i = v.toLowerCase().indexOf(needle.toLowerCase()); if (i < 0) return false;
        const s = v.lastIndexOf('\\n', i) + 1, e = v.indexOf('\\n', i) < 0 ? v.length : v.indexOf('\\n', i);
        t.focus(); t.setSelectionRange(s, e); t.scrollTop = Math.max(0, t.scrollHeight * s / v.length - 80); return v.slice(s, e); }""", [needle])
    if not ok: print("  !! edit target not found:", needle); return
    line = ok
    if needle == "statin":
        import re
        newline = re.sub(r"statin[^;\n]*", "Statin (prescribed, NOT taking)", line, count=1, flags=re.I)
    else:
        newline = "Social history: Smokes 1 ppd x 30 years. Wears a work boot that sometimes gets wet."
    page.keyboard.type(newline, delay=22)
    page.wait_for_timeout(900)

def attending(page, node):
    """Answer the attending's question(s) until Continue / See how it went."""
    for _ in range(4):
        page.wait_for_selector("#god.open", timeout=180_000); idle(page)
        page.wait_for_timeout(2500)
        if page.query_selector("#god-reply"):
            if node == "D1" and not getattr(attending, "dictated", False):
                attending.dictated = True; dictate(page, "god-reply", "abi"); beat("dictated: attending answer")
            else:
                type_in(page, "#god-reply", REPLY.get(node, "I'm not sure."), delay=22)
            page.wait_for_timeout(500); page.evaluate("document.getElementById('god-send').click()"); idle(page)
            continue
        page.wait_for_timeout(3500)
        page.evaluate("document.getElementById('god-ok').click()"); page.wait_for_timeout(1200)
        return

def good(p):
    global T0
    ctx = p.chromium.launch().new_context(viewport={"width": W, "height": H}, record_video_dir=str(OUT / "tmp_good"),
                                          record_video_size={"width": W, "height": H})
    ctx.add_init_script(VMIC)
    ctx.route("**/__clips/*", lambda r: r.fulfill(path=str(CLIPS[r.request.url.rsplit("/", 1)[1][:-4]]), content_type="audio/wav"))
    page = ctx.new_page(); T0 = time.time()
    page.goto(URL); page.wait_for_timeout(2500); beat("start_page")
    page.click('[data-mode="practice"]'); page.wait_for_timeout(1500); beat("encounter")
    for q in INTERVIEW:
        if q.startswith("What kind of shoes"):
            dictate(page, "say", "shoe"); beat("dictated: shoes")
            page.click("#say"); page.keyboard.press("Enter")
        else:
            type_in(page, "#say", q); page.keyboard.press("Enter")
        idle(page); page.wait_for_timeout(1400)
        beat(f"said: {q}")
    page.wait_for_selector("#open-alert:not([hidden])", timeout=60_000); page.wait_for_timeout(3000); beat("alert_badge")
    page.click("#open-alert"); idle(page); page.wait_for_timeout(4500); beat("alert_opened")
    for q in ASK:
        type_in(page, "#ai-q", q); page.keyboard.press("Enter"); idle(page); page.wait_for_timeout(2600)
        beat(f"asked: {q}")
    page.click("#finish-interview"); idle(page); page.wait_for_timeout(3000); beat("note_draft")
    edit_line(page, "statin", None); beat("fixed_statin")
    edit_line(page, "Social history:", None); page.wait_for_timeout(2000); beat("fixed_social")
    type_in(page, "#note-ap", AP["D1"], delay=6); page.wait_for_timeout(1500); beat("ap_typed")
    page.click("#sign"); beat("signed_D1"); attending(page, "D1"); beat("attending_done_D1")
    for node in ("D3", "D4", "D5"):
        page.wait_for_selector("#note-ap", timeout=180_000); idle(page); page.wait_for_timeout(1800)
        cur = page.inner_text("#note-title"); beat(f"note {node}: {cur}")
        type_in(page, "#note-ap", AP[node], delay=6); page.wait_for_timeout(800); page.click("#sign"); beat(f"signed_{node}")
        attending(page, node)
        if node == "D5": break
    page.wait_for_timeout(2500)
    if page.query_selector("#god-ok"): page.click("#god-ok")
    page.wait_for_selector(".report", timeout=240_000); idle(page); page.wait_for_timeout(3000); beat("report")
    for y in range(0, 2400, 6):
        page.evaluate(f"document.querySelector('#god') && (document.querySelector('#god').scrollTop = {y})"); page.wait_for_timeout(16)
    page.wait_for_timeout(2000); beat("end")
    vid = page.video.path(); ctx.close(); Path(vid).rename(OUT / "raw_good.webm")

def faculty(p):
    global T0
    ctx = p.chromium.launch().new_context(viewport={"width": W, "height": H}, record_video_dir=str(OUT / "tmp_fac"),
                                          record_video_size={"width": W, "height": H})
    page = ctx.new_page(); T0 = time.time()
    page.goto(URL + "/#faculty"); page.wait_for_timeout(2500); beat("faculty_list")
    boxes = page.query_selector_all("#saved-list input[type=checkbox]:not([disabled])")[:2]
    for b in boxes: b.check(); page.wait_for_timeout(900)
    page.wait_for_timeout(800); page.click("#compare"); page.wait_for_timeout(6000); beat("compare")
    page.wait_for_timeout(2000); beat("end")
    vid = page.video.path(); ctx.close(); Path(vid).rename(OUT / "raw_faculty.webm")

with sync_playwright() as p:
    {"good": good, "faculty": faculty}[sys.argv[1]](p)
Path(OUT / f"beats_{sys.argv[1]}.json").write_text(json.dumps(beats, indent=1))
