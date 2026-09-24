# -*- coding: utf-8 -*-
"""Colab 무료 T4 에서 LTX-Video i2v 로 8컷 생성. 사용: python colab_i2v.py [출력폴더]"""
import os, sys, torch
from diffusers import LTXImageToVideoPipeline
from diffusers.utils import export_to_video, load_image
OUT = sys.argv[1] if len(sys.argv) > 1 else "/content/out"
os.makedirs(OUT, exist_ok=True)
NEG = "color, colour, text, letters, logo, watermark, face, hands, people, deformation, melting, warping, flicker, blurry, still, frozen"
TAIL = ", black and white, low-key lighting, macro, locked-off camera, one continuous shot"
SHOTS = [
 ("01_O", "the glossy oil film spreads outward across the dark slab, its wet edge creeping forward, a hard highlight sliding across the wet surface"),
 ("02_D", "the thin wet patch shrinks and evaporates away, the surface turning chalky and matte"),
 ("03_R", "the droplet bounces off the taut surface and rolls away as a bright bead, the surface staying flat and still"),
 ("04_S", "the crown splash rises and falls back, concentric ripples race outward to the edges of the frame and slowly settle"),
 ("05_P", "the black ink plume blooms upward and unfurls, spreading slowly into a soft feathered cloud"),
 ("06_N", "a soft band of light glides evenly across the perfectly still clean surface"),
 ("07_T", "the sphere is pressed flat then springs back to round with a small wobble, two tiny droplets flying off"),
 ("08_W", "the press lifts away and the circular crease with radial folds stays pressed into the fabric"),
]
pipe = LTXImageToVideoPipeline.from_pretrained("Lightricks/LTX-Video", torch_dtype=torch.bfloat16)
pipe.enable_model_cpu_offload()
pipe.vae.enable_tiling()
for name, prompt in SHOTS:
    dst = os.path.join(OUT, name + ".mp4")
    if os.path.exists(dst):
        print(name, "skip"); continue
    img = load_image(f"frames/{name}.png")
    v = pipe(image=img, prompt=prompt + TAIL, negative_prompt=NEG,
             width=704, height=1216, num_frames=97, num_inference_steps=40,
             generator=torch.Generator().manual_seed(7)).frames[0]
    export_to_video(v, dst, fps=24)
    print(name, "OK", os.path.getsize(dst))
print("ALL DONE")
