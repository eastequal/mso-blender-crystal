# -*- coding: utf-8 -*-
"""GPU 가 잡히면 한 번에: 8컷 i2v → 25초 조립 → 임시 호스팅 업로드까지.
Colab 셀 하나로 돌린다. 프레임은 저장소 frames/ 에 이미 들어 있다(v17 확정본)."""
import subprocess, os, sys, json, re, urllib.request
def sh(c):
    print("$", c[:110], flush=True)
    return subprocess.run(c, shell=True, capture_output=True, text=True)

sh("pip -q install -U diffusers transformers accelerate imageio imageio-ffmpeg")
sh("apt-get -qq install -y fonts-nanum > /dev/null 2>&1")
r = sh("cd /content/pkg && python -u colab_svd.py /content/out 2>&1 | grep -E 'OK motion|끝 ·|실패'")
print(r.stdout[-1200:], flush=True)
r = sh("cd /content/pkg && python -u colab_build25.py /content/out /content/ad_final.mp4 2>&1 | tail -3")
print(r.stdout[-600:], flush=True)
if os.path.exists("/content/ad_final.mp4"):
    out = sh("curl -s -F 'file=@/content/ad_final.mp4' https://tmpfiles.org/api/v1/upload").stdout
    print("업로드:", out[:200], flush=True)
else:
    print("조립 실패 — ad_final.mp4 없음", flush=True)
