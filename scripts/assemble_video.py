"""Assemble the 3:00 demo cut from the screen recordings (+ optional VO / face clips).
Usage: python3 scripts/assemble_video.py [--vo path.m4a] [--hook face.mp4]
Inputs: video/raw_good.webm, video/raw_faculty.webm, docs/img/architecture.png, video/title.png
Output: video/calibrate_demo.mp4 (1920x1080, 30 fps, H.264)."""
import argparse, subprocess
from pathlib import Path

V = Path("video"); SEG = V / "seg"; SEG.mkdir(parents=True, exist_ok=True)
FONT = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30", "-an"]

def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace(",", "\\,")

def caption(text, y="h-150"):
    return (f"drawtext=fontfile={FONT}:text='{esc(text)}':fontsize=40:fontcolor=white:"
            f"box=1:boxcolor=0x1C2142@0.88:boxborderw=22:x=(w-text_w)/2:y={y}")

def clip(name, src, start, end, speed=1.0, caps=(), hold=0.0):
    """caps = [(t0, t1, text)] in OUTPUT seconds."""
    vf = [f"setpts=(PTS-STARTPTS)/{speed}", "scale=1920:1080:force_original_aspect_ratio=decrease",
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0xE3EBE6", "fps=30"]
    if hold:
        vf.append(f"tpad=stop_mode=clone:stop_duration={hold}")
    for t0, t1, text in caps:
        vf.append(caption(text) + f":enable='between(t,{t0},{t1})'")
    out = SEG / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(start), "-to", str(end), "-i", str(src),
                    "-vf", ",".join(vf), *ENC, str(out)], check=True)
    return out

def still(name, img, dur, caps=()):
    vf = ["scale=1920:1080", "fps=30"] + [caption(t) + f":enable='between(t,{a},{b})'" for a, b, t in caps]
    out = SEG / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-t", str(dur), "-i", str(img),
                    "-vf", ",".join(vf), *ENC, str(out)], check=True)
    return out

def face(name, src, dur):
    out = SEG / f"{name}.mp4"
    lower = (f"drawtext=fontfile={FONT}:text='{esc('Marissa Famularo, DO  ·  Vascular surgeon  ·  Associate Program Director')}':"
             "fontsize=36:fontcolor=white:box=1:boxcolor=0x1C2142@0.85:boxborderw=18:x=60:y=h-130:enable='between(t,1,6)'")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-t", str(dur), "-i", str(src), "-vf",
                    "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30," + lower, *ENC, str(out)], check=True)
    return out

def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True).stdout.strip())

ap = argparse.ArgumentParser(); ap.add_argument("--vo"); ap.add_argument("--hook"); a = ap.parse_args()
G, F = V / "raw_good.webm", V / "raw_faculty.webm"
HOOK = min(duration(a.hook), 36.0) if a.hook else 25.0
SPARE = HOOK - 25.0  # taken back from the grid flash, faculty hold, and architecture so the cut stays 3:00
import json
B = {b["beat"].split(":")[0]: b["t"] for b in json.loads((V / "beats_good.json").read_text())}
enc, badge, opened = B["encounter"], B["alert_badge"], B["alert_opened"]
draft, d3, d5 = B["note_draft"], B["note D3"], B["signed_D5"]
sign1, att_done = B["signed_D1"], B["attending_done_D1"]
parts = [
    face("00_hook", a.hook, HOOK) if a.hook else still("00_hook", V / "title.png", HOOK),
    clip("01_grid", F, 12.3, 13.9, hold=5.4 - min(2.0, SPARE), caps=[(0.5, 6.8, "Calibrate measures how residents rely on AI")]),   # 0:25-0:32
    clip("02_encounter", G, enc, badge, speed=(badge - enc) / 28, caps=[(0.5, 6, "Synthetic patient, played by Muse Spark Open"),
        (12.5, 19.5, "Dictated: Muse Spark Open transcribes the resident's voice")]),
    clip("03_alert", G, badge, badge + 15, caps=[(0.3, 3.5, "The ambient assistant raises an alert")]),         # 1:00-1:15
    clip("04_note", G, draft, draft + 25, caps=[(0.3, 4.5, "AI-drafted note: the resident corrects it before signing")]),  # 1:15-1:40
    clip("05_attending", G, draft + 25, att_done, speed=(att_done - draft - 25) / 18, caps=[(0.3, 3.5, "Practice mode: the attending weighs in"),
        (4, 12.5, "Answer dictated, transcribed by Muse Spark Open")]),     # 1:40-1:55
    clip("06a_ask", G, opened + 4, draft, speed=(draft - opened - 4) / 9.4, caps=[(0, 9.4, "Asks the assistant: endovascular first? (wrong)  ·  antiplatelet, BP, smoking (right, adopted)  ·  sped up")]),
    clip("06b_workup", G, d3, d5, speed=(d5 - d3) / 7.9, caps=[(0, 4.0, "Vein mapping before angiogram  ·  no usable vein  →  tibial angioplasty  ·  sped up"),
                                                         (4.0, 7.9, "Discharge: statin, antiplatelet, cessation, diabetes, BP  ·  sped up")]),  # 1:55-2:15
    clip("07_faculty", F, 0.0, 14.0, hold=13.0 - min(5.0, max(0.0, SPARE - 2.0)), caps=[(0.3, 5, "Faculty view: same case, two residents"),
                                                       (14, 21.5, "Calibrated: wound healed  ·  Overreliant: toe, then TMA, then MI")]),        # 2:15-2:42
    still("08_arch", Path("docs/img/architecture.png"), 18 - max(0.0, SPARE - 7.0), caps=[(9, 14.8, "Built during the hackathon, Oct 27 – Nov 4, 2026")]),  # 2:42-3:00
]
lst = SEG / "list.txt"; lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
silent = V / "calibrate_silent.mp4"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent)], check=True)
out = V / "calibrate_demo.mp4"
ins, flt, n = ["-i", str(silent)], [], 0
if a.hook:
    ins += ["-i", a.hook]; n += 1; flt.append(f"[{n}:a]atrim=0:{HOOK},asetpts=PTS-STARTPTS,highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a{n}]")
if a.vo:
    ins += ["-i", a.vo]; n += 1; d = int(HOOK * 1000); flt.append(f"[{n}:a]highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,adelay={d}|{d}[a{n}]")
if n:
    mix = "".join(f"[a{i}]" for i in range(1, n + 1)) + (f"amix=inputs={n}:normalize=0:duration=longest[aout]" if n > 1 else "anull[aout]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *ins, "-filter_complex", ";".join(flt + [mix]),
                    "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", str(duration(silent)), str(out)], check=True)
else:
    silent.rename(out)
d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                   capture_output=True, text=True).stdout.strip()
print(out, f"{float(d):.1f}s")
