# -*- coding: utf-8 -*-
"""Colab 무료 T4 에서 LTX-Video i2v 로 8컷 생성.
사용: python colab_i2v.py [출력폴더]

🔴 산출물은 «구글 드라이브» 에 쓴다. 9/23 에 세 시간 구운 450프레임을
   휘발성 Colab VM 한 곳에만 두었다가 통째로 잃었다 — 한 컷 끝날 때마다 바로 남긴다.
🔴 T4 는 Turing 이라 bfloat16 을 지원하지 않는다. float16 으로 돈다."""
import os, sys, gc, torch
from diffusers import LTXImageToVideoPipeline
from diffusers.utils import export_to_video, load_image

OUT = sys.argv[1] if len(sys.argv) > 1 else "/content/drive/MyDrive/피부유형_컷"
os.makedirs(OUT, exist_ok=True)

NEG  = ("color, colour, text, letters, logo, watermark, face, hands, people, "
        "falling water, pouring, splashing in, new liquid entering frame, "
        "deformation, melting, warping, flicker, blurry, still, frozen")
TAIL = ", black and white, low-key lighting, macro, locked-off camera, one continuous shot"

SHOTS = [
 ("01_O", "the glossy oil film spreads outward across the dark slab, its wet edge creeping forward, a hard highlight sliding across the wet surface"),
 ("03_R", "the droplet bounces off the taut surface and rolls away as a bright bead, the surface staying flat and still"),
 ("04_S", "the crown splash rises and falls back, concentric ripples race outward to the edges of the frame and slowly settle"),
 # D = 「마른다」 — 물이 «들어오면» 안 된다(9/25 실측: 모델이 물줄기를 떨어뜨려 컷을 버렸다)
 ("02_D", "the dried ring slowly contracts inward as the last moisture evaporates away, the matte surface cracking finer and turning chalky, nothing falls in, no liquid is added"),
 ("05_P", "the dark blot blooms and unfurls outward, spreading slowly into a soft feathered cloud that stays on the surface"),
 ("06_N", "a soft band of light glides evenly across the perfectly clean still surface, leaving nothing behind"),
 ("07_T", "the rounded form is pressed flat then springs back to round with a small wobble, returning to its original shape"),
 ("08_W", "the press lifts away and the crease with radial folds stays pressed into the surface, not recovering"),
]

def build(dtype, w, h, nf, steps):
    p = LTXImageToVideoPipeline.from_pretrained("Lightricks/LTX-Video", torch_dtype=dtype)
    p.enable_model_cpu_offload(); p.vae.enable_tiling()
    return p, w, h, nf, steps

pipe, W, H, NF, STEPS = build(torch.float16, 704, 1216, 97, 40)
print(f"준비 완료 · {W}x{H} · {NF}프레임 · {STEPS}스텝 · fp16")

done, failed = [], []
for name, prompt in SHOTS:
    dst = os.path.join(OUT, name + ".mp4")
    if os.path.exists(dst) and os.path.getsize(dst) > 50_000:
        print(name, "skip"); done.append(name); continue
    img = load_image(f"frames/{name}.png")
    for w, h, nf in [(W, H, NF), (512, 896, 65)]:     # T4 가 모자라면 한 단 낮춰 다시
        try:
            v = pipe(image=img, prompt=prompt + TAIL, negative_prompt=NEG,
                     width=w, height=h, num_frames=nf, num_inference_steps=STEPS,
                     generator=torch.Generator().manual_seed(7)).frames[0]
            export_to_video(v, dst, fps=24)
            print(f"{name} OK {w}x{h} {nf}f {os.path.getsize(dst)//1024}KB → {dst}", flush=True)
            done.append(name); break
        except torch.cuda.OutOfMemoryError:
            print(f"{name} OOM {w}x{h} — 한 단 낮춰 재시도", flush=True)
            gc.collect(); torch.cuda.empty_cache()
        except Exception as e:
            print(f"{name} 실패 {type(e).__name__} {str(e)[:120]}", flush=True)
            failed.append(name); break
    gc.collect(); torch.cuda.empty_cache()

print(f"\n끝 · 성공 {len(done)}/{len(SHOTS)} {done} · 실패 {failed}")
print(f"산출물은 드라이브에 있다 → {OUT}")
