# -*- coding: utf-8 -*-
"""Wan 2.2 TI2V-5B 로 8컷 i2v. 사용: python -u colab_wan.py [출력폴더]

왜 SVD 가 아니라 Wan 인가 (9/26 판단):
  · SVD 는 «텍스트 프롬프트를 아예 안 받는다» — 공들여 만든 프롬프트가 한 글자도 안 들어간다.
  · Wan 2.2 는 텍스트 조건 모델이고, 9/25 실측에서 우리 O 컷에 motion 3.49 를 냈다(전 기간 최고).
프롬프트는 prompt_spec.py 가 정본 — 7슬롯 구조·80~120단어·사람 금지·피부과 맥락."""
import os, sys, gc, torch
from diffusers import WanImageToVideoPipeline, AutoencoderKLWan
from diffusers.utils import export_to_video, load_image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompt_spec import build, NEGATIVE, EVENTS

OUT = sys.argv[1] if len(sys.argv) > 1 else "/content/out"
os.makedirs(OUT, exist_ok=True)
MODEL = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
W, H, NF, FPS = 704, 1216, 49, 16          # 49프레임 ÷ 16fps ≈ 3.1초 (컷 2초 + 여유)

vae = AutoencoderKLWan.from_pretrained(MODEL, subfolder="vae", torch_dtype=torch.float32)
pipe = WanImageToVideoPipeline.from_pretrained(MODEL, vae=vae, torch_dtype=torch.float16)
pipe.enable_model_cpu_offload()             # 램이 12.7GB 뿐이라 필수
try: pipe.vae.enable_tiling()
except Exception: pass
print("Wan 2.2 TI2V-5B 준비 완료 · fp16", flush=True)

done, failed = [], []
for name in EVENTS:
    dst = os.path.join(OUT, name + ".mp4")
    if os.path.exists(dst) and os.path.getsize(dst) > 30_000:
        print(name, "skip", flush=True); done.append(name); continue
    img = load_image(f"frames/{name}.png").resize((W, H))
    try:
        v = pipe(image=img, prompt=build(name), negative_prompt=NEGATIVE,
                 height=H, width=W, num_frames=NF, guidance_scale=5.0,
                 num_inference_steps=30,
                 generator=torch.Generator("cuda").manual_seed(7)).frames[0]
        export_to_video(v, dst, fps=FPS)
        print(f"{name} OK {os.path.getsize(dst)//1024}KB", flush=True); done.append(name)
    except Exception as e:
        print(f"{name} 실패 {type(e).__name__} {str(e)[:140]}", flush=True); failed.append(name)
    gc.collect(); torch.cuda.empty_cache()

print(f"\n끝 · 성공 {len(done)}/{len(EVENTS)} · 실패 {failed}", flush=True)
if failed:
    print("🔴 Wan 이 안 되면 안전망으로 colab_svd.py 를 돌린다(텍스트 프롬프트는 못 쓴다)", flush=True)
