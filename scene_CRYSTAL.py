# -*- coding: utf-8 -*-
"""CRYSTAL 「16면 크리스탈」 — 15초 본편 450프레임 · 한 테이크 (박동균 9/22 선택)
f1~90 은 scene_CRYSTAL_90.py(3초 시안) 과 «픽셀 동일»(궤도·돌리·fov·스윕 앞 90프레임 공식 그대로).
f91~315 8유형 구간: 궤도 등속 계속 · 푸시인 fov 18→15.5 · 스트립이 면을 하나씩 켜서 번쩍임 8회(≈28프레임 간격 · 피크 ≤230)
f316~360 결과 구간: 스윕 지나가고 키·필·스트립 꺼져 림만(평균 15~25) · 카메라 시프트로 결정을 오른쪽으로(좌상단 글자 자리)
f361~450 메시지·CTA: 천천히 돌다 f396~414 마지막 글린트 · f405~436 감속 → f436~450 정지
헤이즈·림 2점·바닥 반사·코어 28%(러프 0.6)·스트립 180W · 모션블러 0.5 · 그레인 없음 · Blender 에 글자 없음."""
import bpy, bmesh, math
import scene_common as C

NF = 450; H = 0.32
R0 = math.radians(25.0) / 89.0          # 앞 90프레임 궤도 속도(rad/frame) — 그대로 잇는다
T90 = lambda f: (f - 1) / 89.0

def az_fn(f):
    if f <= 90: return math.radians(25.0) * (T90(f) - 0.5)               # 원본 공식
    a90 = math.radians(25.0) * (T90(90) - 0.5)
    if f <= 405: return a90 + R0 * (f - 90)
    a405 = a90 + R0 * 315
    if f <= 436:                                                          # 코사인 감속 · 436 에서 속도 0
        u = (f - 405) / 31.0; return a405 + R0 * 31.0 * (math.sin(u * math.pi / 2) * 2 / math.pi)
    return a405 + R0 * 31.0 * (2 / math.pi)

def d_fn(f):
    if f <= 315: return 1.9 * (1 - 0.04 * T90(f))                         # 원본 돌리(−4%/90) 를 315 까지 이어 간다
    return 1.9 * (1 - 0.04 * T90(315))

def fov_fn(f):
    if f <= 90: return 18.0
    if f <= 315: return 18.0 - 2.5 * (f - 90) / 225.0                     # 푸시인 (등속)
    return 15.5

def shift_fn(f):   # f300~340 결정을 오른쪽으로 (좌상단 x 65~600 · y 269~900 비우기)
    return -0.10 * C.smoothstep(300, 340, f)

SPEC = {
    "nfr": NF, "seed": 7, "grain": False, "motion_blur": 0.5, "vignette": 0.6,
    "bloom": {"threshold": 0.9, "size": 6, "mix": 0.15},
    "cam": {"fov": 18, "dist": 1.9, "low_angle": 4.0, "orbit": 25.0, "orbit_ease": "linear", "dolly": 0.04, "dolly_ease": "linear", "subj_y": 820, "fstop": 2.8,
            "az_fn": az_fn, "d_fn": d_fn, "fov_fn": fov_fn, "shift_fn": shift_fn},
    "lights": {"key_w": 30, "kf_ratio": 12, "rim_mult": 2.0,
               "key": {"pos": (-0.9, -0.5, 0.9), "size": 0.8, "size_y": 0.8, "mult": 0.5},
               "rim": [{"pos": (-0.8, 0.9, 0.35), "size": 0.06, "spread": 30, "only": ["Crystal"]}, {"pos": (0.8, 0.9, 0.35), "size": 0.06, "spread": 30, "only": ["Crystal"]}],
               "fill": {"pos": (1.0, -0.8, 0.3), "size": 1.0}},
    "haze": {"pos": (0.0, 0.35, 0.18), "radius": 0.5, "density": 0.0002},
    "orb": None,
}

# 스트립 (9/22 프리뷰·스캔 실측으로 확정)
# · 번쩍임의 정체 = 결정 «뒤» 스트립의 몸체가 면을 통해 굴절돼 보이는 것 → 밝기는 에너지와 무관(8W 도 255) · 위치(x)와 궤도각이 맞을 때만 켜진다
# · 그래서 피크 = «x 정렬 + 에너지 펄스»로 만든다: 목표 프레임마다 스캔에서 가장 밝았던 x 에 스트립을 두고 ±7프레임만 켠다(그 밖은 0 → 우연한 번쩍임 없음)
PEAKS = [100 + 28 * k for k in range(8)]
PEAK_X = {100: 0.1, 128: -0.5, 156: -1.3, 184: -0.9, 212: -0.5, 240: 0.1, 268: 1.3, 296: -1.3}
GLINT_X = 1.0; PULSE_W = 60.0; GLINT_W = 60.0
def _pulse(f, c, hw=7):
    u = abs(f - c) / hw
    return 0.5 * (1 + math.cos(math.pi * u)) if u < 1 else 0.0
def strip_x(f):
    if f <= 90: return -1.3 + 2.6 * T90(f)
    keys = [(90, 1.3)] + [(c, PEAK_X[c]) for c in PEAKS] + [(315, -1.3), (395, -1.3), (396, GLINT_X)]
    if f >= 396: return GLINT_X
    for (f0, x0), (f1, x1) in zip(keys, keys[1:]):
        if f0 <= f <= f1: return x0 + (x1 - x0) * (f - f0) / (f1 - f0)
    return -1.3
def strip_w(f):
    if f <= 90: return 180.0
    if f <= 93: return 180.0 * (1 - (f - 90) / 3.0)                        # 원본 180 → 0 (앞 90프레임 끝에서 스트립은 화면 밖 x=+1.3)
    if f <= 315: return PULSE_W * max(_pulse(f, c) for c in PEAKS)
    if 396 <= f <= 414: return GLINT_W * _pulse(f, 405, 9)                  # 마지막 글린트 (피크 f405)
    return 0.0
def keyfill_mult(f):   # 결과 구간부터 키·필 0 (림만)
    return 1.0 - C.smoothstep(316, 330, f)

def build(ctx):
    sc = ctx["scene"]
    C.dark_plane("Floor", size=10.0, base=0.02, rough=0.08, coat=1.0, z=0.0)
    me = bpy.data.meshes.new("Crystal"); bm = bmesh.new()
    r = H * 0.36; zb = H * 0.28; top = H
    ring = [bm.verts.new((r * math.cos(2 * math.pi * i / 8), r * math.sin(2 * math.pi * i / 8), zb)) for i in range(8)]
    vt = bm.verts.new((0, 0, top)); vb = bm.verts.new((0, 0, 0.0))
    for i in range(8):
        bm.faces.new((ring[i], ring[(i + 1) % 8], vt)); bm.faces.new((ring[(i + 1) % 8], ring[i], vb))
    bm.to_mesh(me); bm.free()
    cr = bpy.data.objects.new("Crystal", me); sc.collection.objects.link(cr); cr.location = (0, 0, 0.001)
    glass, gb = C.principled("CrystalGlass", **{"Base Color": (0.95, 0.95, 0.95, 1), "Transmission Weight": 1.0, "IOR": 1.55, "Roughness": 0.02, "Coat Weight": 0.3, "Coat Roughness": 0.03})
    cr.data.materials.append(glass)
    for p in me.polygons: p.use_smooth = False
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=H * 0.28 * 0.5, location=(0, 0, H * 0.42)); core = bpy.context.object; core.name = "Core"; bpy.ops.object.shade_smooth()
    cm, _ = C.principled("Core", **{"Base Color": (0.02, 0.02, 0.02, 1), "Roughness": 0.6, "Specular IOR Level": 0.1}); core.data.materials.append(cm)
    ctx["subject_center"] = lambda f: (0.0, 0.0, H * 0.45)
    ctx["aim_target"] = cr
    ctx["post_lights"] = _post

def _post(ctx):
    sc = ctx["scene"]
    st = bpy.data.lights.new("Strip", "AREA"); st.shape = "RECTANGLE"; st.size = 0.06; st.size_y = 1.4; st.energy = 180.0; st.volume_factor = 1.0
    so = bpy.data.objects.new("Strip", st); sc.collection.objects.link(so); so.visible_camera = False; so.visible_glossy = False
    coll = bpy.data.collections.new("StripOnly"); coll.objects.link(bpy.data.objects["Crystal"]); coll.objects.link(bpy.data.objects["Core"]); so.light_linking.receiver_collection = coll
    c = so.constraints.new("TRACK_TO"); c.target = bpy.data.objects["Crystal"]; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
    key = ctx["lights"]["KeySoftbox"][1]; fill = ctx["lights"]["Fill"][1]; kw, fw = key.energy, fill.energy
    for f in range(1, NF + 1):
        so.location = (strip_x(f), 1.1, 0.55); so.keyframe_insert("location", frame=f)
        st.energy = strip_w(f); st.keyframe_insert("energy", frame=f)
        key.energy = kw * keyfill_mult(f); key.keyframe_insert("energy", frame=f)
        fill.energy = fw * keyfill_mult(f); fill.keyframe_insert("energy", frame=f)
    ctx["lights"]["Strip"] = (so, st)
