# -*- coding: utf-8 -*-
"""Colab 무료 T4 에서 Stable Video Diffusion 으로 8컷 생성.
사용: python -u colab_svd.py [출력폴더]

왜 SVD 인가 (2026-09-26 실측 경로):
  · LTX-Video  → 가중치 23.4GB 를 다 받고 T5 텍스트 인코더를 올리다 시스템 램 12.7GB 에서 OOM 킬.
  · I2VGen-XL  → 최신 diffusers 에서 폐기돼 8/8 이 AttributeError 로 죽음.
  · SVD        → 텍스트 인코더가 «없다»(CLIP 비전만). fp16 5GB 라 램이 남고, 애초에
                 「정지 사진 한 장을 영화처럼 움직이게」 하려고 만든 모델이다.
  · 프롬프트가 없다는 게 오히려 안전장치다 — 9/25 에 Wan 이 D 컷 「마른다」에
                 물줄기를 지어내 컷을 버렸는데, SVD 는 그림에 없는 것을 못 만든다.
🔴 T4 는 Turing 이라 bfloat16 이 없다 — float16 으로만 돈다."""
import os, sys, gc, torch
from diffusers import StableVideoDiffusionPipeline
from diffusers.utils import export_to_video, load_image

OUT = sys.argv[1] if len(sys.argv) > 1 else "/content/out"
os.makedirs(OUT, exist_ok=True)

W, H, NF, FPS_OUT = 576, 1024, 25, 10      # 25프레임 ÷ 10fps = 2.5초 (컷 2초 + 여유)
# 움직임 세기 — 9/25 실측 기준선: 실사 광고 motion 중앙 3~4.5, 우리 목표 2.5 이상
SHOTS = [
    ("01_O", 170),   # 기름이 번진다 — 크게
    ("03_R", 150),   # 튕겨 낸다 — 방울만 움직이고 바닥은 고요해야
    ("04_S", 190),   # 파문 — 가장 크게
    ("02_D", 120),   # 마른다 — 느리게
    ("05_P", 165),   # 번져 남는다
    ("06_N",  95),   # 고르게 남는다 — 가장 고요하게(유형의 뜻이 「없음」이다)
    ("07_T", 180),   # 눌러도 돌아온다 — 탄성
    ("08_W", 110),   # 자국이 남는다 — 안 돌아온다
]

pipe = StableVideoDiffusionPipeline.from_pretrained(
    "stabilityai/stable-video-diffusion-img2vid-xt",
    torch_dtype=torch.float16, variant="fp16")
pipe.enable_model_cpu_offload()
pipe.unet.enable_forward_chunking()
print(f"파이프라인 준비 완료 · fp16 · SVD-XT · {W}x{H} {NF}프레임", flush=True)

done, failed = [], []
for name, motion in SHOTS:
    dst = os.path.join(OUT, name + ".mp4")
    if os.path.exists(dst) and os.path.getsize(dst) > 30_000:
        print(name, "skip", flush=True); done.append(name); continue
    img = load_image(f"frames/{name}.png").resize((W, H))
    try:
        v = pipe(img, height=H, width=W, num_frames=NF,
                 decode_chunk_size=2, motion_bucket_id=motion,
                 noise_aug_strength=0.05,
                 generator=torch.manual_seed(7)).frames[0]
        export_to_video(v, dst, fps=FPS_OUT)
        print(f"{name} OK motion_bucket={motion} {os.path.getsize(dst)//1024}KB", flush=True)
        done.append(name)
    except Exception as e:
        print(f"{name} 실패 {type(e).__name__} {str(e)[:140]}", flush=True)
        failed.append(name)
    gc.collect(); torch.cuda.empty_cache()

print(f"\n끝 · 성공 {len(done)}/{len(SHOTS)} {done} · 실패 {failed}", flush=True)
