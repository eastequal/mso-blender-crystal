# -*- coding: utf-8 -*-
"""판(PNG 시퀀스) 위에 Remotion 스크림을 «시뮬레이션»해서 흰 글자 최악 대비를 잰다.
쓰는 곳 = Colab (판을 내려받기 전에 스크림 배율을 정하기 위해). 인자: 판 폴더 [프레임수]
글자 자리 = x 65~600 · y 269~900 (V10 좌상단 예약 구간) · 기준선 79."""
import sys, math
import numpy as np
from PIL import Image

W, H = 1080, 1920
D = sys.argv[1] if len(sys.argv) > 1 else "/content/out/CRYSTAL2"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 450

def diag(stops, deg=105.0):
    th = math.radians(deg); dx, dy = math.sin(th), -math.cos(th)
    L = abs(W * math.sin(th)) + abs(H * math.cos(th))
    xs = np.arange(W)[None, :] - W / 2
    ys = np.arange(H)[:, None] - H / 2
    t = 0.5 + (xs * dx + ys * dy) / L
    return np.clip(np.interp(t, [s[0] for s in stops], [s[1] for s in stops]), 0, 1)

HOOK = diag([(0, .50), (.30, .28), (.55, 0), (1, 0)])
RUN  = diag([(0, .62), (.32, .35), (.58, 0), (1, 0)])
END  = np.clip(np.interp(np.arange(H)[:, None] / H, [0, .45, .70, 1], [.55, .25, 0, 0]), 0, 1) * np.ones((1, W))

KS = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
best = {k: (999, 0) for k in KS}
for n in range(1, N + 1):
    P = np.asarray(Image.open(f"{D}/f{n:03d}.png").convert("L"), float)
    A = HOOK if n <= 90 else (RUN if n <= 315 else END)
    for k in KS:
        a = np.clip(A * k, 0, 1)
        z = (P * (1 - a) + 17 * a)[269:900, 65:600]
        c = 255 - z.max()
        if c < best[k][0]:
            best[k] = (c, n)
print(f"판 {D} · {N}장 · 글자자리 x65~600 y269~900 · 기준선 79")
for k in KS:
    c, n = best[k]
    print(f"  스크림 {k:.1f}배 → 최악대비 {c:6.1f} (f{n:03d}) {'OK' if c >= 79 else '미달'}")
