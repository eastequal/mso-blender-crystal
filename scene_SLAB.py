# -*- coding: utf-8 -*-
"""시안 3 · SLAB 「빛과 안개 속 석판」 — 90프레임 · 하나의 세계 · 하나의 카메라 · 컷 없음
헤이즈 0.0006(이방성 0.6) 속 위에서 내려오는 볼류메트릭 스팟(콘 25° · 하드) 하나 · 무광 석판(0.35 · 1.2×0.8×0.12 · 베벨) 이 3초에 12° 돌고 · 빛기둥이 표면을 훑어 긴 그림자 · 먼지 3천 · 카메라 50mm 로우앵글 · 돌리 +5%"""
import bpy, math
import scene_common as C

NF = 90
SPEC = {
    "nfr": NF, "seed": 7, "grain": False, "motion_blur": 0.5, "vignette": 0.6, "exposure": 0.0,
    "bloom": {"threshold": 0.9, "size": 6, "mix": 0.12},
    "cam": {"fov": 27, "dist": 2.3, "elev": 9.0, "dolly": 0.05, "dolly_ease": "linear", "subj_y": 1180, "fstop": 4.0},   # 고도 9° → 윗면이 원근으로 보인다   # v2: 카메라 높이 ≈0.15m 로우앵글 · 석판 폭 80% · 공중 빛기둥이 위 1/3
    "lights": {"key_w": 0.001, "kf_ratio": 1, "rim_mult": 1.0,
               "key": {"pos": (0, 0, 5), "size": 0.1}, "rim": [], "fill": None},
    "haze": None, "orb": None,
}

def build(ctx):
    sc = ctx["scene"]; world = ctx["world"]
    wn = world.node_tree.nodes; wl = world.node_tree.links
    vol = wn.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = 0.40; vol.inputs["Anisotropy"].default_value = 0.85   # v3 실측: 빛기둥은 «역광 + 전방산란»에서만 읽힌다 (0.015·측광은 top1/3 0.2 → 0.40·후방 스팟은 49)
    ctx["scene"].cycles.volume_bounces = 1; ctx["scene"].cycles.volume_step_rate = 0.5
    wl.new(vol.outputs["Volume"], wn["World Output"].inputs["Volume"])
    C.dark_plane("Floor", size=30.0, base=0.04, rough=0.7, coat=0.0, z=0.0)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.06 + 0.05))
    slab = bpy.context.object; slab.name = "Slab"; slab.scale = (1.2, 0.8, 0.12)
    bpy.ops.object.transform_apply(scale=True); C.bevel(slab, 0.012, 4)
    m, b = C.principled("Stone", **{"Base Color": (0.14, 0.14, 0.14, 1), "Roughness": 0.72, "Specular IOR Level": 0.35})
    C.roughness_noise(m, b, base=0.72, amp=0.06, scale=30)
    n, l = m.node_tree.nodes, m.node_tree.links
    tc = n.new("ShaderNodeTexCoord"); g1 = n.new("ShaderNodeTexNoise"); g1.inputs["Scale"].default_value = 90.0; g1.inputs["Detail"].default_value = 6.0; g1.inputs["Roughness"].default_value = 0.7; l.new(tc.outputs["Object"], g1.inputs["Vector"])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35; bp.inputs["Distance"].default_value = 0.0015; l.new(g1.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs["Normal"], b.inputs["Normal"])
    slab.data.materials.append(m)
    for f in range(1, NF + 1):
        t = (f - 1) / (NF - 1)
        slab.rotation_euler = (math.radians(2.0), math.radians(-1.5), math.radians(30.0 - 6.0 + 12.0 * t))   # v2: 30° 돌려 모서리 원근; slab.keyframe_insert("rotation_euler", frame=f)
    aim = bpy.data.objects.new("SpotAim", None); sc.collection.objects.link(aim)
    so, sl = C.spot(ctx, "Beam", (0.6, 3.0, 1.4), 800.0, size_deg=10, blend=0.15, radius=0.05, target=aim)   # v3: 뒤-위-오른쪽에서 카메라 쪽으로(역광) · 콘 10° → 공중 기둥
    sl.volume_factor = 1.0
    for f in range(1, NF + 1):
        t = (f - 1) / (NF - 1)
        aim.location = (-0.30 + 0.60 * t, -0.75 + 0.10 * t, 0.10); aim.keyframe_insert("location", frame=f)   # 빔이 석판 «위를 스쳐» 앞 바닥에 닿는다 → 윗면은 반그늘·기둥은 공중
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.0066, location=(0, 0, -5)); mote = bpy.context.object; mote.name = "Mote"
    mm, mb = C.principled("Mote", **{"Base Color": (0.9, 0.9, 0.9, 1), "Roughness": 0.6}); mote.data.materials.append(mm); mote.hide_render = True
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.3, 1.2, 0.9)); emit = bpy.context.object; emit.name = "DustVolume"; emit.scale = (1.2, 2.2, 1.6); emit.hide_render = True; emit.display_type = "WIRE"
    bpy.context.view_layer.objects.active = emit
    bpy.ops.object.particle_system_add(); ps = emit.particle_systems[0]; ps.seed = 7; s = ps.settings
    s.count = 3000; s.frame_start = -200; s.frame_end = -1; s.lifetime = 600; s.emit_from = "VOLUME"; s.physics_type = "NEWTON"
    s.mass = 0.001; s.normal_factor = 0.0; s.brownian_factor = 0.015; s.drag_factor = 0.5; s.effector_weights.gravity = 0.0
    s.render_type = "OBJECT"; s.instance_object = mote; s.particle_size = 1.0; s.size_random = 0.6
    try: emit.show_instancer_for_render = False
    except Exception: pass
    ctx["subject_center"] = lambda f: (0.0, 0.0, 0.10)
    ctx["aim_target"] = None
    ctx["post_lights"] = _post

def _post(ctx):
    ctx["lights"]["KeySoftbox"][0].hide_render = True
    rim, rl = C.area(ctx, "RimBack", (-0.6, 2.4, 0.9), 0.12, 60.0, "DISK", None, 40, volume=0.0, target=bpy.data.objects["Slab"])
    coll = bpy.data.collections.new("RimOnly"); coll.objects.link(bpy.data.objects["Slab"]); rim.light_linking.receiver_collection = coll
