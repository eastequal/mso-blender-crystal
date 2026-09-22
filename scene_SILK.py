# -*- coding: utf-8 -*-
"""시안 1 · SILK 「흑백 실크의 흐름」 — 90프레임 · 짙은 회색 실크 2×3m 클로스 시뮬(위 두 모서리 핀 · 바람 3.5 + 난류 · 감쇠 낮게)
천 폭의 1/3 이 프레임 · 왼쪽 뒤 고도 15° 스트립이 능선을 스침 · 오른쪽 아래 필 1/10 · 시인 1.0 · 코트 0.2 · 이방성 · 100mm 상당 · 트럭 6%/3초 + 살짝 틸트
시뮬 실패(변위 없음) 시 셰이프키 파도 3겹으로 대체하고 ctx["silk_fallback"]=True 로 보고"""
import bpy, math
import scene_common as C

NF = 90; W, Hc = 2.0, 3.0; PRE = 60   # bake 1~150 · 렌더 = 시뮬 61~150 (1~30 위 모서리 모으기 → 주름 형성)
FORCE_FALLBACK = False   # v2: 클로스 시뮬 정공법(위 모서리 한 줄 핀 · 바람 2m/s 옆-아래 · 난류 4/0.6 애니) · 실패 시 저주파 노이즈 변위
SPEC = {
    "nfr": NF, "seed": 7, "grain": False, "motion_blur": 0.5, "vignette": 0.6,
    "bloom": {"threshold": 0.9, "size": 6, "mix": 0.12},
    "cam": {"fov": 20, "dist": 5.0, "elev": 3.0, "lateral": 0.06, "lateral_ease": "linear", "tilt_up": 1.5, "tilt_ease": "linear", "subj_y": 760, "fstop": 5.6},   # v2: 천 폭 1/2 · 천을 32° 돌려 비스듬히
    "lights": {"key_w": 1100, "kf_ratio": 10, "rim_mult": 1.0,
               "key": {"pos": (-3.2, -2.2, 2.6), "size": 0.06, "size_y": 3.0},   # v2: 왼쪽 위 고도 ≈20° 스침 → 능선 하이라이트 긴 곡선
               "rim": [],
               "fill": {"pos": (2.2, -2.0, -0.6), "size": 1.5}},
    "haze": None, "orb": None,
}

def build(ctx):
    sc = ctx["scene"]
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=60, y_subdivisions=90, size=1.0, location=(0, 0, 0))
    silk = bpy.context.object; silk.name = "Silk"; silk.scale = (W, Hc, 1.0); bpy.ops.object.transform_apply(scale=True)
    silk.rotation_euler = (math.radians(90), 0, 0); bpy.ops.object.transform_apply(rotation=True)
    silk.location = (0, 0, 1.5); bpy.ops.object.transform_apply(location=True); bpy.ops.object.shade_smooth()
    silk.rotation_euler = (0, 0, math.radians(32))   # 비스듬히 → 주름이 대각선
    me = silk.data
    vg = silk.vertex_groups.new(name="Pin")
    zmax = max(v.co.z for v in me.vertices)
    for v in me.vertices:
        if v.co.z > zmax - 0.001: vg.add([v.index], 1.0, "REPLACE")   # v2: 위 모서리 한 줄 전부 핀
    # v3: 핀 줄을 프리롤 1~30 프레임에 절반 폭으로 «모은다» → 중력이 세로 주름을 만든다 (평평한 커튼은 핀 폭 = 천 폭이라 주름이 없다 · 9/22 실측 y-std 0.006 → 0.03)
    top = [v.index for v in me.vertices if v.co.z > zmax - 0.001]
    silk.shape_key_add(name="Basis"); gk = silk.shape_key_add(name="Gather", from_mix=False)
    for i in top: gk.data[i].co.x = me.vertices[i].co.x * 0.5; gk.data[i].co.z = me.vertices[i].co.z + math.tan(math.radians(25)) * me.vertices[i].co.x * 0.5   # 핀 줄 25° 기울임 → 주름이 사선으로 흐른다
    gk.value = 0.0; gk.keyframe_insert("value", frame=1); gk.value = 1.0; gk.keyframe_insert("value", frame=30)
    bpy.context.view_layer.objects.active = silk
    bpy.ops.object.modifier_add(type="CLOTH"); cl = silk.modifiers["Cloth"]; cs = cl.settings
    cs.quality = 6; cs.mass = 0.3; cs.tension_stiffness = 5; cs.compression_stiffness = 5; cs.shear_stiffness = 5; cs.bending_stiffness = 0.05; cs.air_damping = 1.0; cs.vertex_group_mass = "Pin"   # v2: 실크 프리셋
    bpy.ops.object.modifier_add(type="SUBSURF"); silk.modifiers["Subdivision"].levels = 1; silk.modifiers["Subdivision"].render_levels = 2
    bpy.ops.object.effector_add(type="WIND", location=(-2.6, -0.4, -0.3)); wind = bpy.context.object; wind.name = "Wind"
    wind.rotation_euler = (0, math.radians(70), math.radians(25)); wind.field.strength = 2.0; wind.field.noise = 0.5; wind.field.seed = 7   # 옆-아래에서 2 m/s
    bpy.ops.object.effector_add(type="TURBULENCE", location=(0.3, -0.5, 1.4)); tb = bpy.context.object; tb.name = "Turb"
    tb.field.strength = 4.0; tb.field.size = 0.6; tb.field.flow = 0.2; tb.field.noise = 0.6; tb.field.seed = 7
    for fr, (x, z) in ((1, (-0.8, 0.6)), (45, (0.4, 1.9)), (90, (-0.5, 1.1)), (130, (0.7, 2.0))):
        tb.location = (x, -0.5, z); tb.keyframe_insert("location", frame=fr)
    m, b = C.principled("Silk", **{"Base Color": (0.16, 0.16, 0.16, 1), "Roughness": 0.36, "Sheen Weight": 1.0, "Sheen Roughness": 0.4, "Coat Weight": 0.2, "Coat Roughness": 0.15, "Anisotropic": 0.7})
    C.roughness_noise(m, b, base=0.36, amp=0.04, scale=40)
    n, l = m.node_tree.nodes, m.node_tree.links
    tc = n.new("ShaderNodeTexCoord"); wv = n.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 260.0; wv.inputs["Distortion"].default_value = 2.0; l.new(tc.outputs["UV"], wv.inputs["Vector"])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.06; bp.inputs["Distance"].default_value = 0.0003; l.new(wv.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs["Normal"], b.inputs["Normal"])
    silk.data.materials.append(m)
    # 시뮬 → 셰이프키 굽기 (Blender 는 scene.frame_start 하한이 0 이라 음수 프리롤이 안 돈다 · 9/22 실측: 캐시 "not exact" 로 1프레임만 계산)
    # 프레임 1..PRE+NF 를 순차 계산하고 PRE 이후 90장을 셰이프키로 옮긴 뒤 클로스를 뗀다 → 결정적 · 모션블러(변형) 유지
    sm = silk.modifiers["Subdivision"]; sm.show_viewport = False
    sc.frame_start = 1; sc.frame_end = NF + PRE; cl.point_cache.frame_start = 1; cl.point_cache.frame_end = NF + PRE
    base = [v.co.copy() for v in me.vertices]; caps = []
    # 헤드리스에선 frame_set 만으로 클로스가 안 돈다(프리롤 드레이프만) → ptcache.bake 를 컨텍스트 오버라이드로 직접 호출 (9/22 실측)
    try:
        with bpy.context.temp_override(scene=sc, active_object=silk, object=silk, point_cache=cl.point_cache):
            bpy.ops.ptcache.bake(bake=True)
        print("SILK_BAKE", cl.point_cache.is_baked, cl.point_cache.info)
    except Exception as e: print("SILK_BAKE_ERR", e)
    for f in range(1, NF + PRE + 1):
        sc.frame_set(f)
        if f > PRE:
            dg = bpy.context.evaluated_depsgraph_get(); ev = silk.evaluated_get(dg); em = ev.to_mesh()
            caps.append([v.co.copy() for v in em.vertices]); ev.to_mesh_clear()
    disp = max((caps[44][i] - base[i]).length for i in range(0, len(base), 37)) if len(caps[44]) == len(base) else 0.0
    swing = max((caps[89][i] - caps[0][i]).length for i in range(0, len(base), 37)) if len(caps[0]) == len(base) else 0.0
    import statistics; fold = statistics.pstdev([caps[44][i].y for i in range(0, len(base), 7)])
    print("SILK_FOLD f45 y-std", round(fold, 3))
    print("SILK_SIM f45 max disp", round(disp, 3), "| f1→f90 swing", round(swing, 3))
    silk.modifiers.remove(cl); sc.frame_end = NF; sm.show_viewport = True
    gk.value = 0.0; silk.data.shape_keys.animation_data_clear()   # 프레임 셰이프키(절대 좌표)만 남긴다
    ctx["silk_fallback"] = False
    if FORCE_FALLBACK or disp < 0.05 or swing < 0.03 or fold < 0.02:
        ctx["silk_fallback"] = True; print("SILK_SIM FAIL -> shape-key waves x3 fallback")
        import random; random.seed(7)
        G = [(random.random() * 2 * math.pi, random.uniform(0.7, 1.3)) for _ in range(6)]
        def waves(f, x, h):
            t = (f - 1) / 89.0; u = x + 0.9 * t; v = h - 0.6 * t
            z = 0.0
            for k, (ang, sc_) in enumerate(G):
                px = u * math.cos(ang) + v * math.sin(ang)
                z += math.sin(px / (0.8 * sc_) * 2 * math.pi + k) * (0.6 if k < 3 else 0.4)
            return 0.08 * z / 3.0 * C.smoothstep(2.95, 2.3, h)
        C.frame_shape_keys(silk, waves, axis=1, use_z=True)
    else:
        for k, co in enumerate(caps, start=1):
            sk = silk.shape_key_add(name=f"F{k:02d}", from_mix=False)
            for i, c in enumerate(co): sk.data[i].co = c
            for g in range(1, NF + 1):
                sk.value = 1.0 if g == k else 0.0; sk.keyframe_insert("value", frame=g)
    sc.frame_set(1)
    ctx["subject_center"] = lambda f: (-0.1, 0.0, 1.35)
    ctx["aim_target"] = silk
