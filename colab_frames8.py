# -*- coding: utf-8 -*-
"""8유형 첫 프레임을 «한 판 위» 에서 일관되게. 사용: python -u colab_frames8.py [출력폴더]

모델 = Realistic Vision V5.1 — 박동균의 Open Generative AI 앱이 쓰는 그 모델이다.
로컬 앱으로도 되지만 그 노트북은 내장 GPU 2GB 라 장당 5~10분에 compute failed 가 난다(9/26 실측).
같은 모델을 T4 에서 돌려 결과는 같고 시간만 줄인다.

🔴 설계 = 「한 방울이 여덟 표면을 건너간다」 — 시드·판·조명·카메라를 고정하고 «반응»만 바꾼다.
   컷마다 소재가 달라서 여덟 조각으로 보이던 것(v16)이 어색함의 원인이었다."""
import os, sys, torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

OUT = sys.argv[1] if len(sys.argv) > 1 else "/content/frames8"
os.makedirs(OUT, exist_ok=True)

HEAD = "extreme macro photograph of "
TAIL = (" on a smooth dark matte slab, fine surface micro-texture, black and white, low key, "
        "single hard rim light from the left, shallow depth of field, photorealistic product commercial still")
NEG  = ("color, text, letters, watermark, logo, face, person, people, hands, skin, body, portrait, "
        "blurry, cartoon, illustration, painting, low quality, deformed, extra objects")

SHOTS = [
 ("01_O", "a clear oil film spreading outward from a droplet, glossy wet sheen creeping across the surface"),
 ("02_D", "the last thin wet patch shrinking away, the surface around it dry chalky and finely cracked"),
 ("03_R", "dozens of water droplets beaded up tight and round, sitting high and not spreading at all"),
 ("04_S", "a droplet striking the surface, a crown splash at the center and wide concentric ripple rings racing outward"),
 ("05_P", "one dark stain soaked into the surface with feathered edges, clearly darker than the slab around it"),
 ("06_N", "the surface perfectly clean and even, a droplet lifted away leaving no mark at all"),
 ("07_T", "a round dimple pressed into the surface springing back to flat, the surface taut and smooth"),
 ("08_W", "a deep crease with many fine parallel fold lines pressed permanently into the surface"),
]
SEED = 77

pipe = StableDiffusionPipeline.from_pretrained(
    "SG161222/Realistic_Vision_V5.1_noVAE", torch_dtype=torch.float16, safety_checker=None)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("cuda")
pipe.set_progress_bar_config(disable=True)
print("Realistic Vision V5.1 준비 완료 · fp16", flush=True)

for name, event in SHOTS:
    dst = os.path.join(OUT, name + ".png")
    if os.path.exists(dst): print(name, "skip", flush=True); continue
    g = torch.Generator("cuda").manual_seed(SEED)          # 판·조명이 흔들리지 않게 고정
    im = pipe(prompt=HEAD + event + TAIL, negative_prompt=NEG,
              width=512, height=896, num_inference_steps=28,
              guidance_scale=6.0, generator=g).images[0]
    im.resize((704, 1216)).save(dst)                        # SVD 입력 규격
    print(f"{name} OK", flush=True)
print("끝", flush=True)
