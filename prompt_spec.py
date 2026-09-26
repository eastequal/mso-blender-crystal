# -*- coding: utf-8 -*-
"""피부유형 8컷 — 영상 모델(Wan 2.2 i2v) 프롬프트 확정본 v1.
근거: 7슬롯 구조 · Wan 최적 80~120단어 · i2v 는 「움직임+카메라」 · 한 클립 한 사건.
🔴 사람 금지가 최우선 제약 — Pollinations 가 「soft·leather·skin」에서 사람을 뱉은 실측(9/26)."""

# ── 고정 스캐폴드 : 여덟 컷이 «같은 광·같은 렌즈»여야 이어 붙였을 때 한 편으로 보인다 ──
SHOT_TIGHT = "Extreme macro shot, 100mm macro lens, very shallow depth of field"
SHOT_WIDE  = "Wider macro shot, 50mm lens, the whole surface in frame, shallow depth of field"
FRAMING = {"01_O":SHOT_TIGHT, "02_D":SHOT_TIGHT,   # 짝1 — 번진다 / 마른다
           "03_R":SHOT_WIDE,  "04_S":SHOT_WIDE,    # 짝2 — 튕긴다 / 파문
           "05_P":SHOT_TIGHT, "06_N":SHOT_TIGHT,   # 짝3 — 남는다 / 안 남는다
           "07_T":SHOT_WIDE,  "08_W":SHOT_WIDE}    # 짝4 — 돌아온다 / 안 돌아온다
LIGHT = ("one hard rim light from camera left rakes across the surface, deep black falloff on the right, "
         "a single bright specular highlight")
LOOK  = ("black and white, bleach-bypass grade, fine 35mm grain, clinical skincare commercial for a "
         "dermatology clinic, laboratory-clean, premium product film")
PACE  = ("smooth slow motion with a steady even pace, one continuous shot, "
         "the surrounding surface and background remain static, "
         "nothing enters or leaves the frame, no cuts")

# ── 컷마다 «사건 하나 + 카메라 하나» (Wan 공식) ──
EVENTS = {
 "01_O": ("a glossy oil film creeps outward across the matte surface, its wet edge advancing steadily "
          "and the specular highlight sliding along with it", "the camera pushes in very slowly"),
 "02_D": ("the last thin wet patch contracts and evaporates, the surface turning chalky as fine "
          "hairline cracks spread outward", "the camera pushes in very slowly"),
 "03_R": ("dozens of beaded droplets tremble and hold their round shape without spreading, one of them "
          "rolling a short way and stopping", "the camera drifts slowly to the right"),
 "04_S": ("concentric ripple rings race outward from the centre to the edge of the frame, one after "
          "another, then slowly settle flat", "fixed camera"),
 "05_P": ("a dark stain blooms outward into the surface, its feathered edge creeping and then holding, "
          "the mark staying where it is", "the camera pushes in very slowly"),
 "06_N": ("a wide soft band of light glides evenly across the flawless surface from left to right, "
          "leaving the surface completely unchanged", "fixed camera"),
 "07_T": ("a round dimple in the surface lifts and smooths itself back to flat, the surface springing "
          "taut again with one small settling wobble", "fixed camera"),
 "08_W": ("the fine parallel fold lines deepen and hold, the crease refusing to smooth out while the "
          "raking light travels slowly along it", "the camera drifts slowly to the left"),
}

# ── 네거티브 : Wan 기본에서 «overall gray» 를 «뺀다» (흑백 광고라 정반대로 작동한다) ──
# 우선순위대로 추리고 중복을 걷어냈다 — ①사람(절대조건) ②글자·로고 ③정지 ④품질·왜곡 ⑤장면전환
# 🔴 「77토큰 한계」는 CLIP 을 쓰는 SD 계열 이야기이고 Wan 에는 «해당 없다»(umT5·5,000자).
#    본문이 120토큰쯤 되는 것은 Wan 최적 구간(80~120단어)에 맞춘 것이지 초과가 아니다.
NEGATIVE = ("person, people, face, hands, fingers, skin, body, "
            "text, watermark, logo, subtitles, "
            "static, frozen, still picture, "
            "bright colors, oversaturated, overexposed, low quality, jpeg artifacts, "
            "deformed, melting, warping, flicker, morphing, "
            "new objects entering frame, scene change, cut")

def build(key):
    ev, cam = EVENTS[key]
    return f"{FRAMING[key]}. {ev}, {cam}. {LIGHT}. {LOOK}. {PACE}."

# 조립기가 프롬프트의 «카메라 의도»와 어긋나지 않게 — fixed 인 컷에 푸시인을 걸면 서로 싸운다
CAMERA = {k: ("push" if "pushes in" in v[1] else "drift_r" if "to the right" in v[1]
              else "drift_l" if "to the left" in v[1] else "fixed") for k, v in EVENTS.items()}

if __name__ == "__main__":
    print(f"{'컷':<8}{'단어':>5}  판정")
    for k in EVENTS:
        p = build(k); n = len(p.split())
        ok = "OK" if 80 <= n <= 120 else ("길다" if n > 120 else "짧다")
        print(f"{k:<8}{n:>5}  {ok}")
    print(f"\n네거티브 {len(NEGATIVE.split())} 단어")
    print("\n── 예시 (01_O) ──\n" + build("01_O"))
