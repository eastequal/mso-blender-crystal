# -*- coding: utf-8 -*-
"""CRYSTAL2 「16면 크리스탈 · 시네마틱 승격판」 — 450프레임 한 테이크 (9/22 박동균 「시네마틱 급이 아닌데?」 뒤)
CRYSTAL(v1) 과 «궤도·돌리·fov·스트립 피크» 전부 동일 — 바뀐 것은 넷뿐이다.
  ① 랙 포커스   — 초점이 앞면에서 코어로, CTA 에서 다시 앞면으로 옮겨 간다(focus_fn)
  ② 카우스틱    — 결정 아래 바닥에 굴절 무늬를 흘린다(고보 스팟 · 바닥에만 링크 · 피크에 맞춰 펄스)
  ③ 글레어      — 아나모픽 스트리크(현재 v1 은 글레어 0) · 탈색 뒤 S곡선 앞
  ④ 모션블러 0.5→0.7 + 바닥 반사에 미세 물결(웨이브 범프 · 프레임마다 흐른다)
나머지는 scene_CRYSTAL.py 와 같은 코드다."""

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
    "nfr": NF, "seed": 7, "grain": False, "motion_blur": 0.7, "vignette": 0.6,
    "bloom": {"threshold": 0.9, "size": 6, "mix": 0.15},
    "cam": {"fov": 18, "dist": 1.9, "low_angle": 4.0, "orbit": 25.0, "orbit_ease": "linear", "dolly": 0.04, "dolly_ease": "linear", "subj_y": 820, "fstop": 2.8,
            "az_fn": az_fn, "d_fn": d_fn, "fov_fn": fov_fn, "shift_fn": shift_fn, "focus_fn": lambda f: focus_fn(f)},
    "lights": {"key_w": 30, "kf_ratio": 12, "rim_mult": 2.0,
               "key": {"pos": (-0.9, -0.5, 0.9), "size": 0.8, "size_y": 0.8, "mult": 0.5},
               "rim": [{"pos": (-0.8, 0.9, 0.35), "size": 0.06, "spread": 30, "only": ["Crystal"]}, {"pos": (0.8, 0.9, 0.35), "size": 0.06, "spread": 30, "only": ["Crystal"]}],
               "fill": {"pos": (1.0, -0.8, 0.3), "size": 1.0}},
    # ⑥ 대기 — v1 은 밀도 0.0002 라 사실상 없었다. 림·스트립 빛이 «공기에 걸려» 보이는 것이 시네마틱의 큰 몫이다.
    "haze": {"pos": (0.0, 0.30, 0.22), "radius": float(__import__("os").environ.get("HAZE_R", 0.85)),
             "density": float(__import__("os").environ.get("HAZE_D", 0.0015))},
    "orb": None,
    # ③ 글레어 — 아나모픽 2줄(수평). 임계 1.0 이라 면 반사 피크만 늘어난다(평상 화면엔 안 걸린다).
    "glare": {"type": "Streaks", "quality": "High", "threshold": 0.85, "strength": 0.95,
              "size": 0.72, "streaks": 2, "angle": 0.0, "fade": 0.90, "iterations": 3, "smoothness": 0.15},
}

# ① 랙 포커스 — 음수 = 초점이 카메라 쪽(앞면) · 0 = 결정 중심
#    훅(1~75) 앞면 → 코어 · 런 내내 코어 · CTA 글린트(396~436) 다시 앞면으로 당긴다
def focus_fn(f):
    if f <= 75: return -0.055 * (1 - C.ease_in_out_sine(f / 75.0))
    if f < 396: return 0.0
    if f <= 436: return -0.045 * C.ease_in_out_sine((f - 396) / 40.0)
    return -0.045

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
    _floor_ripple(C.dark_plane("Floor", size=10.0, base=0.02, rough=0.08, coat=1.0, z=0.0))
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
    _caustics(ctx)   # ❌ _backdrop 은 안 부른다 — 9/23 스윕 실측 화면 기여 0(헤이즈가 그 자리를 대신한다)


# ② 카우스틱 고보 — 결정 아래 바닥에만 닿는 스팟. 보로노이 「모서리까지 거리」를 얇은 선으로 잘라
#    굴절 무늬처럼 만들고, 면이 켜지는 피크에 맞춰 세게 흘린다(그 밖은 0 이라 우연한 무늬 없음).
import os
CAUS_W = float(os.environ.get("CAUS_W", 3500.0))  # 바닥 알베도 0.02 라 420W 는 화면에 0 이었다(9/23 스윕) · 2500 부터 결정 내부가 읽힌다
def caus_w(f):
    if f <= 90: return CAUS_W * 0.35
    if f <= 315: return CAUS_W * (0.25 + 0.75 * max(_pulse(f, c, 11) for c in PEAKS))
    if f <= 360: return CAUS_W * 0.25 * (1 - C.smoothstep(316, 355, f))
    if 396 <= f <= 436: return CAUS_W * 0.8 * _pulse(f, 412, 22)
    return 0.0

def _backdrop(ctx):
    """결정 뒤 소프트 그라데이션 벽 — 방사형으로 중앙만 아주 옅게(0~0.055) 뜬다. 검정은 검정으로 남는다."""
    sc = ctx["scene"]
    bpy.ops.mesh.primitive_plane_add(size=7.0, location=(0.0, 2.6, 1.2), rotation=(math.radians(90), 0, 0))
    bd = bpy.context.object; bd.name = "Backdrop"
    m = bpy.data.materials.new("Backdrop"); m.use_nodes = True
    nt = m.node_tree; n, l = nt.nodes, nt.links
    out = n["Material Output"]
    for nd in list(n):
        if nd.type == "BSDF_PRINCIPLED": n.remove(nd)
    em = n.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.0
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (0.5, 0.5, 0.0); mp.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    gr = n.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"
    rp = n.new("ShaderNodeValToRGB")
    rp.color_ramp.elements[0].position = 0.30; rp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1)
    rp.color_ramp.elements[1].position = 1.0;  rp.color_ramp.elements[1].color = (0.055, 0.055, 0.055, 1)
    l.new(tc.outputs["Generated"], mp.inputs["Vector"]); l.new(mp.outputs["Vector"], gr.inputs["Vector"])
    l.new(gr.outputs["Fac"], rp.inputs["Fac"]); l.new(rp.outputs["Color"], em.inputs["Color"])
    l.new(em.outputs["Emission"], out.inputs["Surface"])
    bd.data.materials.append(m)
    bd.visible_shadow = False
    return bd

def _caustics(ctx):
    sc = ctx["scene"]
    ld = bpy.data.lights.new("Caustic", "SPOT")
    ld.spot_size = math.radians(58); ld.spot_blend = 0.55; ld.shadow_soft_size = 0.02; ld.energy = 0.0
    ld.use_nodes = True
    nt = ld.node_tree; n, l = nt.nodes, nt.links
    em = n.get("Emission") or n.new("ShaderNodeEmission")
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    vo = n.new("ShaderNodeTexVoronoi"); vo.feature = "DISTANCE_TO_EDGE"
    vo.inputs["Scale"].default_value = 13.0
    try: vo.inputs["Randomness"].default_value = 0.85
    except Exception: pass
    rp = n.new("ShaderNodeValToRGB")                 # 얇은 선만 남긴다
    rp.color_ramp.elements[0].position = 0.0;  rp.color_ramp.elements[0].color = (1, 1, 1, 1)
    rp.color_ramp.elements[1].position = 0.085; rp.color_ramp.elements[1].color = (0, 0, 0, 1)
    l.new(tc.outputs["Normal"], mp.inputs["Vector"]); l.new(mp.outputs["Vector"], vo.inputs["Vector"])
    l.new(vo.outputs["Distance"], rp.inputs["Fac"]); l.new(rp.outputs["Color"], em.inputs["Color"])
    o = bpy.data.objects.new("Caustic", ld); sc.collection.objects.link(o)
    o.location = (0.0, 0.10, 0.62); o.visible_camera = False
    coll = bpy.data.collections.new("CausticOnly"); coll.objects.link(bpy.data.objects["Floor"])
    try: o.light_linking.receiver_collection = coll
    except Exception as e: print("caustic light_linking", e)
    for f in range(1, NF + 1):
        ld.energy = caus_w(f); ld.keyframe_insert("energy", frame=f)
        mp.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(0.09) * f)   # 궤도와 같은 방향으로 아주 느리게
        mp.inputs["Rotation"].keyframe_insert("default_value", frame=f)
    ctx.setdefault("lights", {})["Caustic"] = (o, ld)

# ④ 바닥 미세 물결 — 링 웨이브 범프. 프레임마다 위상이 흘러 반사가 잔잔히 떨린다(변위 아님 · 노멀만).
def _floor_ripple(floor):
    m = floor.data.materials[0]; nt = m.node_tree; n, l = nt.nodes, nt.links
    b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping")
    wv = n.new("ShaderNodeTexWave"); wv.wave_type = "RINGS"; wv.bands_direction = "DIAGONAL"
    wv.inputs["Scale"].default_value = 3.2; wv.inputs["Distortion"].default_value = 6.0
    wv.inputs["Detail"].default_value = 2.0
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.035; bp.inputs["Distance"].default_value = 0.02
    l.new(tc.outputs["Object"], mp.inputs["Vector"]); l.new(mp.outputs["Vector"], wv.inputs["Vector"])
    l.new(wv.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs["Normal"], b.inputs["Normal"])
    for f in range(1, NF + 1):
        mp.inputs["Location"].default_value = (0.0, 0.0022 * f, 0.0)
        mp.inputs["Location"].keyframe_insert("default_value", frame=f)
