# -*- coding: utf-8 -*-
"""Colab 무료 T4 에서 I2VGen-XL 로 8컷 생성. 사용: python colab_i2vgen.py [출력폴더]

🔴 LTX 를 안 쓰는 이유 = 2026-09-26 실측. Colab 무료는 시스템 램이 12.7GB 인데
   LTX 의 T5 텍스트 인코더를 올리다 「Loading checkpoint shards 50%」 에서 OOM 킬러가 죽였다.
   I2VGen-XL 은 fp16 전량이 8GB 안쪽이고 게이트도 없다.
🔴 T4 는 Turing 이라 bfloat16 이 없다 — float16 으로만 돈다."""
import os, sys, gc, torch
from diffusers import I2VGenXLPipeline
from diffusers.utils import export_to_video, load_image

OUT = sys.argv[1] if len(sys.argv) > 1 else "/content/out"
os.makedirs(OUT, exist_ok=True)

NEG  = ("color, colour, text, letters, logo, watermark, face, hands, people, "
        "falling water, pouring, new liquid entering frame, "
        "distortion, deformation, melting, warping, flicker, blurry, low quality, frozen, static")
TAIL = ", black and white, monochrome, low-key lighting, extreme macro, locked-off camera, cinematic"

SHOTS = [
 ("01_O", "glossy oil film spreading outward across a dark slab, the wet edge creeping forward, a hard highlight sliding across the wet surface"),
 ("03_R", "a droplet bouncing off a taut surface and rolling away as a bright bead, the surface staying flat"),
 ("04_S", "a crown splash rising and falling back, concentric ripples racing outward and slowly settling"),
 ("02_D", "a dried ring contracting inward as the last moisture evaporates, the matte surface turning chalky and finely cracked"),
 ("05_P", "a dark blot blooming and unfurling outward into a soft feathered cloud that stays on the surface"),
 ("06_N", "a soft band of light gliding evenly across a perfectly clean still surface, leaving nothing behind"),
 ("07_T", "a rounded form pressed flat then springing back to round with a small wobble, returning to its shape"),
 ("08_W", "a press lifting away while the crease with radial folds stays pressed into the surface, not recovering"),
]

pipe = I2VGenXLPipeline.from_pretrained("ali-vilab/i2vgen-xl",
                                        torch_dtype=torch.float16, variant="fp16")
pipe.enable_model_cpu_offload()
print("파이프라인 준비 완료 · fp16 · I2VGen-XL", flush=True)

done, failed = [], []
for name, prompt in SHOTS:
    dst = os.path.join(OUT, name + ".mp4")
    if os.path.exists(dst) and os.path.getsize(dst) > 30_000:
        print(name, "skip", flush=True); done.append(name); continue
    img = load_image(f"frames/{name}.png").resize((704, 1280))
    try:
        v = pipe(prompt=prompt + TAIL, image=img, negative_prompt=NEG,
                 num_inference_steps=50, guidance_scale=9.0,
                 num_frames=16, target_fps=16,
                 generator=torch.manual_seed(7)).frames[0]
        export_to_video(v, dst, fps=8)          # 16프레임 ÷ 8fps = 2초 = 컷 길이 그대로
        print(f"{name} OK {os.path.getsize(dst)//1024}KB → {dst}", flush=True)
        done.append(name)
    except Exception as e:
        print(f"{name} 실패 {type(e).__name__} {str(e)[:140]}", flush=True)
        failed.append(name)
    gc.collect(); torch.cuda.empty_cache()

print(f"\n끝 · 성공 {len(done)}/{len(SHOTS)} {done} · 실패 {failed}", flush=True)
