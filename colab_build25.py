# -*- coding: utf-8 -*-
"""Colab 안에서 8컷을 25초 세로 광고로 조립. 사용: python -u colab_build25.py [컷폴더] [출력]
로컬 build_v14.py 와 같은 규격 — 1080x1920 30fps · 모노크롬 · 로고/얼굴/손 없음 · 무음으로도 전부 읽힘.
세이프에어리어: 위 14퍼센트(269) · 아래 35퍼센트(1248 아래) · 좌우 6퍼센트 → 자막은 y 269~1248 · x 65~1015."""
import os, sys, subprocess, numpy as np
from PIL import Image

CUT = sys.argv[1] if len(sys.argv) > 1 else "/content/out"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/content/피부유형_25초.mp4"
TMP = "/content/build25"; os.makedirs(TMP, exist_ok=True)

W, H, FPS = 1080, 1920, 30
FG, DIM, BGC = "0xF8F8F8", "0x5E5E5E", "0x111111"
FB = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
FR = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"

CUTS = [
    ("01_O", "O", "지성",     "기름이 번진다"),
    ("02_D", "D", "건성",     "물기가 마른다"),
    ("03_R", "R", "저항성",   "튕겨 낸다"),
    ("04_S", "S", "민감성",   "파문이 퍼진다"),
    ("05_P", "P", "색소성",   "번져 남는다"),
    ("06_N", "N", "비색소성", "고르게 남는다"),
    ("07_T", "T", "탄력성",   "눌러도 돌아온다"),
    ("08_W", "W", "주름성",   "자국이 남는다"),
]
CUT_SEC = 2.0

# 하단 스크림 — 0.36H 에서 0.62H 까지 smoothstep 으로 올려 자막이 밝은 바닥에 안 묻히게
SCRIM = os.path.join(TMP, "scrim.png")
y = np.arange(H)[:, None].astype(float)
t = np.clip((y - H*0.50) / (H*0.20), 0, 1); t = t*t*(3-2*t)
a = (t*205).astype(np.uint8)
img = np.zeros((H, W, 4), np.uint8); img[..., 3] = np.repeat(a, W, axis=1)
Image.fromarray(img, "RGBA").save(SCRIM)

def run(args):
    r = subprocess.run(args, capture_output=True)
    if r.returncode:
        sys.stderr.write(r.stderr.decode("utf-8", "ignore")[-1500:]); raise SystemExit("ffmpeg 실패")

def esc(s): return s.replace("\\", "\\\\").replace(":", "\:").replace("'", "’").replace("%", "\%")
def dt(text, font, size, color, x, yy):
    return f"drawtext=fontfile={font}:text='{esc(text)}':fontsize={size}:fontcolor={color}:x={x}:y={yy}"

seg, got = [], []
for i, (stem, ch, ko, line) in enumerate(CUTS, 1):
    src = os.path.join(CUT, stem + ".mp4")
    if not os.path.exists(src): print(f"  [빠짐] {stem}"); continue
    dst = os.path.join(TMP, f"c{i:02d}.mp4")
    fc = (f"[0:v]minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
          f"scale=-2:{int(H*1.10)},crop={int(W*1.10)}:{int(H*1.10)},"
          f"zoompan=z='1+0.085*on/{int(CUT_SEC*FPS)-1}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
          f"format=gray,format=yuv420p[v];[1:v]scale={W}:{H}[s];"
          f"[v][s]overlay=0:0[b];[b]{dt(ch,FB,168,FG,96,920)},{dt(ko,FB,66,FG,100,1112)},"
          f"{dt(line,FR,44,DIM,100,1196)},fps={FPS}[o]")
    # 🔴 i2v 산출물은 첫 1~2프레임에 노이즈가 남는다 — 0.2초를 버리고 시작한다
    run(["ffmpeg","-y","-v","error","-ss","0.2","-i",src,"-i",SCRIM,"-filter_complex",fc,"-map","[o]",
         "-t",str(CUT_SEC),"-an","-c:v","libx264","-pix_fmt","yuv420p","-crf","18",dst])
    seg.append(dst); got.append(f"{ch} {ko}"); print(f"  컷 {ch} {ko}", flush=True)
if not seg: raise SystemExit("컷이 없다")

def card(name, dur, layers, bed, dark):
    dst = os.path.join(TMP, name + ".mp4")
    fc = (f"[0:v]minterpolate=fps={FPS}:mi_mode=blend,scale=-2:{H},crop={W}:{H},format=gray,format=yuv420p,"
          f"eq=brightness={dark}:contrast=0.92[v];[1:v]scale={W}:{H}[s];[v][s]overlay=0:0[b];[b]"
          + ",".join(layers) + f",fps={FPS}[o]")
    run(["ffmpeg","-y","-v","error","-stream_loop","4","-i",bed,"-i",SCRIM,"-filter_complex",fc,
         "-map","[o]","-t",str(dur),"-an","-c:v","libx264","-pix_fmt","yuv420p","-crf","18",dst])
    return dst

bed0 = os.path.join(CUT, "02_D.mp4") if os.path.exists(os.path.join(CUT,"02_D.mp4")) else os.path.join(CUT,"01_O.mp4")
bedL = os.path.join(CUT, "08_W.mp4") if os.path.exists(os.path.join(CUT,"08_W.mp4")) else bed0

hook = card("hook", 3.0, [dt("같은 화장품을 써도",    FR, 54, DIM, 100, 556),
                          dt("결과가 다른 이유",      FB, 88, FG, 100, 636),
                          dt("피부를 가르는 축 여덟", FR, 50, DIM, 100, 1120)], bed0, -0.30)
msg  = card("msg", 2.5, [dt("내 피부 관리는",         FB, 84, FG, 100, 790),
                         dt("내 피부를 아는 것부터.",  FB, 84, FG, 100, 906)], bedL, -0.35)
cta  = card("cta", 3.5, [dt("내 피부 유형 알아보기 ↑", FB, 76, FG, 100, 706),
                         dt("16문항 · 1분",            FR, 52, DIM, 100, 842),
                         dt("페이스필터의원 수원점",   FR, 44, DIM, 100, 1178)], bed0, -0.38)

lst = os.path.join(TMP, "list.txt")
with open(lst, "w", encoding="utf-8") as f:
    for p in [hook] + seg + [msg, cta]: f.write(f"file '{p}'\n")
run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",lst,
     "-c:v","libx264","-pix_fmt","yuv420p","-crf","18","-r",str(FPS),"-an",OUT])

d = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",OUT],
                   capture_output=True).stdout.decode().strip()
print(f"\n완성 {OUT} · {float(d):.2f}초 · 유형컷 {len(seg)}/8 ({', '.join(got)}) · {os.path.getsize(OUT)//1024}KB", flush=True)
