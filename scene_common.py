# -*- coding: utf-8 -*-
"""8장면 공통 리그 (Blender 5.2 LTS · Cycles CPU 32spp + OIDN · 1080×1920 · 30fps · 흑백)
정본 = 광고영상_기획서_260921.md 「컷 2 v6 두 겹 브리프」 공통 + 3D품질_리서치_260922.md.
장면 모듈은 SPEC(dict) 과 build(ctx) 를 내고, render.py 가 setup → build → finalize → render 순으로 부른다."""
import bpy, math, os, random

W, H, FPS, NFR = 1080, 1920, 30, 30

# ---------- 이징 ----------
def clamp01(t): return max(0.0, min(1.0, t))
def ease_out_cubic(t): t = clamp01(t); return 1 - (1 - t) ** 3
def ease_out_quad(t): t = clamp01(t); return 1 - (1 - t) ** 2
def ease_out_quart(t): t = clamp01(t); return 1 - (1 - t) ** 4
def ease_in_out_sine(t): t = clamp01(t); return -(math.cos(math.pi * t) - 1) / 2
def ease_in_out(t): t = clamp01(t); return t * t * (3 - 2 * t)
def linear_then_ease(t, tail=0.15):
    """선형으로 가다 마지막 tail 구간만 ease-out (R 금속)"""
    t = clamp01(t); k = 1 - tail
    if t <= k: return t
    u = (t - k) / tail
    return k + tail * (1 - (1 - u) ** 2)
def smoothstep(a, b, x):
    t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t)
EASE = {"easeOutCubic": ease_out_cubic, "easeOutQuad": ease_out_quad, "easeOutQuart": ease_out_quart,
        "easeInOutSine": ease_in_out_sine, "linearTail": linear_then_ease, "none": lambda t: 0.0, "linear": clamp01}

# ---------- 초기화 ----------
def setup(spec, args):
    global NFR
    NFR = int(spec.get("nfr", 30))   # v9: 장면별 프레임 수
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = int(args.res)
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, NFR
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"; sc.render.image_settings.color_depth = "8"
    vs = sc.view_settings
    vs.view_transform = "AgX"; vs.look = "AgX - High Contrast"; vs.exposure = spec.get("exposure", 0.0); vs.gamma = 1.0
    world = bpy.data.worlds.new("Void"); sc.world = world; world.use_nodes = True
    bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0, 0, 0, 1); bg.inputs["Strength"].default_value = 0.0
    random.seed(spec.get("seed", 7))
    ctx = {"scene": sc, "world": world, "spec": spec, "args": args, "subject_center": lambda f: (0.0, 0.0, 0.0), "focus_offset": (0, 0, 0)}
    return ctx

# ---------- 재질 ----------
def principled(name, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    for k, v in kw.items():
        b.inputs[k].default_value = v
    return m, b

def roughness_noise(m, b, base=0.5, amp=0.05, scale=40.0):
    """CG 티 처방: 거칠기 균일 금지 → 노이즈 ±amp"""
    n, l = m.node_tree.nodes, m.node_tree.links
    tex = n.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = scale; tex.inputs["Detail"].default_value = 4
    mr = n.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = base - amp; mr.inputs["To Max"].default_value = base + amp
    l.new(tex.outputs["Fac"], mr.inputs["Value"]); l.new(mr.outputs["Result"], b.inputs["Roughness"])

def dark_plane(name, size=6.0, base=0.02, rough=0.5, coat=0.0, z=0.0):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    o = bpy.context.object; o.name = name
    m, b = principled(name, **{"Base Color": (base, base, base, 1), "Roughness": rough, "Coat Weight": coat, "Coat Roughness": 0.05})
    o.data.materials.append(m); return o

def bevel(obj, width=0.0012, segments=3):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_add(type="BEVEL"); obj.modifiers["Bevel"].width = width; obj.modifiers["Bevel"].segments = segments

def grid(name, size_x, size_y, sub, z=0.0):
    """세분화 평면 (정점 ≤ 10만 규칙 — sub 300 이면 9만)"""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=sub, y_subdivisions=sub, size=1.0, location=(0, 0, z))
    o = bpy.context.object; o.name = name; o.scale = (size_x, size_y, 1.0)
    bpy.ops.object.transform_apply(scale=True); bpy.ops.object.shade_smooth()
    return o

def frame_shape_keys(obj, disp_fn, axis=2, use_z=False):
    """프레임마다 셰이프키 하나: disp_fn(f, x, y) → 변위. 값 키프레임으로 그 프레임에만 1. (Wave 모디파이어가 헤드리스에서 안 움직여 대체 · 9/22)"""
    me = obj.data
    if not me.shape_keys: obj.shape_key_add(name="Basis")
    base = [v.co.copy() for v in me.vertices]
    for f in range(1, NFR + 1):
        sk = obj.shape_key_add(name=f"F{f:02d}", from_mix=False)
        for i, co in enumerate(base):
            d = disp_fn(f, co.x, co.z if use_z else co.y)   # use_z: 세로로 매달린 천은 높이가 z
            c = co.copy(); c[axis] += d; sk.data[i].co = c
        for g in range(1, NFR + 1):
            sk.value = 1.0 if g == f else 0.0; sk.keyframe_insert("value", frame=g)

# ---------- 조명 ----------
def area(ctx, name, loc, size, power, shape="RECTANGLE", size_y=None, spread=None, volume=0.0, target=None):
    sc = ctx["scene"]
    ld = bpy.data.lights.new(name, "AREA"); ld.shape = shape; ld.size = size
    if size_y: ld.size_y = size_y
    ld.energy = power; ld.color = (1, 1, 1)
    try: ld.volume_factor = volume
    except Exception: pass
    if spread is not None:
        try: ld.spread = math.radians(spread)
        except Exception: pass
    o = bpy.data.objects.new(name, ld); sc.collection.objects.link(o); o.location = loc
    o.visible_camera = False
    tgt = target or ctx.get("aim_target")
    if tgt is not None:
        c = o.constraints.new("TRACK_TO"); c.target = tgt; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
    ctx.setdefault("lights", {})[name] = (o, ld)
    return o, ld

def spot(ctx, name, loc, power, size_deg=30, blend=0.9, radius=0.15, target=None, diffuse=1.0, specular=1.0):
    sc = ctx["scene"]; ld = bpy.data.lights.new(name, "SPOT"); ld.energy = power; ld.spot_size = math.radians(size_deg); ld.spot_blend = blend; ld.shadow_soft_size = radius
    try: ld.diffuse_factor = diffuse; ld.specular_factor = specular
    except Exception: pass
    o = bpy.data.objects.new(name, ld); sc.collection.objects.link(o); o.location = loc; o.visible_camera = False
    if target is not None:
        c = o.constraints.new("TRACK_TO"); c.target = target; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
    ctx.setdefault("lights", {})[name] = (o, ld); return o, ld

def build_lights(ctx):
    """spec['lights'] = {key_w, kf_ratio, rim_mult, key:{pos,size,size_y}, rim:[{pos,size,spread,mult?}], fill:{pos,size}}"""
    L = ctx["spec"]["lights"]; kw = L["key_w"]
    k = L["key"]; area(ctx, "KeySoftbox", k["pos"], k["size"], kw * k.get("mult", 1.0), "RECTANGLE", k.get("size_y", k["size"]))
    for i, r in enumerate(L.get("rim", [])):
        o, ld = area(ctx, f"Rim{i}", r["pos"], r["size"], kw * r.get("mult", L.get("rim_mult", 1.5)), r.get("shape", "DISK"), None, r.get("spread", 30), volume=1.0)
        if r.get("only"):
            # 라이트 링킹: 이 림은 지정 오브젝트(+헤이즈)만 비춘다 → 바닥 스필 0 (9/22 실측: R·T 바닥이 림 원뿔에 탔다)
            coll = bpy.data.collections.new(f"RimOnly{i}")
            for nm in r["only"] + ["Haze"]:
                ob = bpy.data.objects.get(nm)
                if ob is not None and ob.name not in coll.objects: coll.objects.link(ob)
            try: o.light_linking.receiver_collection = coll
            except Exception as e: print("light_linking", e)
            ctx.setdefault("rim_only", []).append(coll)
    f = L.get("fill")
    if f: area(ctx, "Fill", f["pos"], f["size"], kw / L["kf_ratio"], "RECTANGLE", f.get("size_y", f["size"]))

# ---------- 헤이즈 (림 방향에만 · 구 볼륨 · 중심→가장자리 0 · 림만 볼륨을 비춘다) ----------
def build_haze(ctx):
    hz = ctx["spec"].get("haze")
    if not hz: return
    dens = hz.get("density", 0.0002)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=hz.get("radius", 0.30), location=hz["pos"])
    haze = bpy.context.object; haze.name = "Haze"; haze.display_type = "WIRE"
    hm = bpy.data.materials.new("Haze"); hm.use_nodes = True
    hn = hm.node_tree.nodes; hl = hm.node_tree.links
    for n in list(hn):
        if n.type != "OUTPUT_MATERIAL": hn.remove(n)
    vol = hn.new("ShaderNodeVolumePrincipled"); vol.inputs["Anisotropy"].default_value = 0.6
    vol.inputs["Absorption Color"].default_value = (1, 1, 1, 1)
    tc = hn.new("ShaderNodeTexCoord"); ln = hn.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"
    hl.new(tc.outputs["Object"], ln.inputs[0])
    mr = hn.new("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"
    mr.inputs["From Min"].default_value = 0.10; mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value = dens; mr.inputs["To Max"].default_value = 0.0
    hl.new(ln.outputs["Value"], mr.inputs["Value"]); hl.new(mr.outputs["Result"], vol.inputs["Density"])
    hl.new(vol.outputs["Volume"], hn["Material Output"].inputs["Volume"])
    haze.data.materials.append(hm)
    try: haze.visible_shadow = False
    except Exception: pass
    for coll in ctx.get("rim_only", []):
        if haze.name not in coll.objects: coll.objects.link(haze)

# ---------- 원거리 단일 광원 = 먼 곳의 원형 그라디언트 발광판 ----------
def build_orb(ctx):
    ob = ctx["spec"].get("orb")
    if not ob: return
    rot = ob.get("rot", (math.radians(90), 0, 0))
    bpy.ops.mesh.primitive_plane_add(size=ob.get("size", 9.0), location=ob["pos"], rotation=rot)
    bd = bpy.context.object; bd.name = "FarLightGradient"
    bm = bpy.data.materials.new("FarLight"); bm.use_nodes = True
    bn = bm.node_tree.nodes; bl = bm.node_tree.links
    for n in list(bn):
        if n.type != "OUTPUT_MATERIAL": bn.remove(n)
    tc = bn.new("ShaderNodeTexCoord"); gr = bn.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"
    mp = bn.new("ShaderNodeMapping"); s = 1.0 / ob.get("radius", 1.7); mp.inputs["Scale"].default_value = (s, s, s)
    bl.new(tc.outputs["Object"], mp.inputs["Vector"]); bl.new(mp.outputs["Vector"], gr.inputs["Vector"])
    pw = bn.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = ob.get("power", 1.6)
    bl.new(gr.outputs["Fac"], pw.inputs[0])
    em = bn.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = ob.get("emit", 0.28)
    bl.new(pw.outputs[0], em.inputs["Color"]); bl.new(em.outputs["Emission"], bn["Material Output"].inputs["Surface"])
    bd.data.materials.append(bm)
    # 카메라·굴절에만 보이고 바닥을 비추지 않는다 (9/22 실측: R·T 바닥이 이 판 때문에 하얗게 탔다)
    for attr, val in (("visible_shadow", False), ("visible_diffuse", False), ("visible_glossy", False), ("visible_volume_scatter", False)):
        try: setattr(bd, attr, val)
        except Exception: pass

# ---------- 카메라 리그 ----------
def build_camera(ctx):
    """spec['cam'] = {fov, dist, low_angle(카메라가 피사체보다 아래·양수) 또는 elev, dolly, dolly_ease, subj_y 또는 subj_y_fn,
       orbit, orbit_ease, tilt_up, tilt_ease, lateral, follow, fstop}"""
    sc = ctx["scene"]; C = ctx["spec"]["cam"]
    fov = math.radians(C["fov"])
    cd = bpy.data.cameras.new("Cam"); cd.sensor_fit = "VERTICAL"; cd.sensor_height = 24.0
    cd.lens = 12.0 / math.tan(fov / 2); cd.clip_start = 0.005
    cd.shift_x = C.get("shift_x", 0.0)   # 세로 프레임 기준 · 양수면 피사체가 «왼쪽»으로 → 오른쪽에 두려면 음수
    cd.dof.use_dof = (not ctx["args"].nodof) and C.get("fstop", 1.8) < 22; cd.dof.aperture_fstop = C.get("fstop", 1.8); cd.dof.aperture_blades = 9   # fstop ≥ 22 = DoF off
    cam = bpy.data.objects.new("Camera", cd); sc.collection.objects.link(cam); sc.camera = cam
    aim = bpy.data.objects.new("Aim", None); sc.collection.objects.link(aim)
    con = cam.constraints.new("TRACK_TO"); con.target = aim; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    el = math.radians(C.get("elev", -C.get("low_angle", 10.0)))   # 음수 = 카메라가 아래에서 위를 본다
    dolly_e = EASE[C.get("dolly_ease", "easeOutCubic")]; orbit_e = EASE[C.get("orbit_ease", "linearTail")]
    tilt_e = EASE[C.get("tilt_ease", "easeOutQuad")]; lat_e = EASE[C.get("lateral_ease", "easeOutCubic")]
    follow = C.get("follow", 1.0)
    c0 = ctx["subject_center"](1)
    for f in range(1, NFR + 1):
        t = (f - 1) / (NFR - 1)
        d = C["d_fn"](f) if "d_fn" in C else C["dist"] * (1 - C.get("dolly", 0.0) * dolly_e(t))
        az = C["az_fn"](f) if "az_fn" in C else math.radians(C.get("orbit", 0.0)) * (orbit_e(t) - 0.5)
        if "fov_fn" in C:
            fov = math.radians(C["fov_fn"](f)); cd.lens = 12.0 / math.tan(fov / 2); cd.keyframe_insert("lens", frame=f)
        if "shift_fn" in C:
            cd.shift_x = C["shift_fn"](f); cd.keyframe_insert("shift_x", frame=f)
        sy = C["subj_y_fn"](t) if "subj_y_fn" in C else C.get("subj_y", 700)
        off = math.atan((0.5 - sy / 1920.0) * 2 * math.tan(fov / 2))
        cen = ctx["subject_center"](f)
        anchor = tuple(c0[i] + follow * (cen[i] - c0[i]) for i in range(3))
        lat = C.get("lateral", 0.0) * C["dist"] * lat_e(t)
        cx = anchor[0] + d * math.sin(az) * math.cos(el) + lat
        cy = anchor[1] - d * math.cos(az) * math.cos(el)
        cz = anchor[2] + d * math.sin(el)
        cam.location = (cx, cy, cz)
        dx, dy, dz = cen[0] - cx + lat, cen[1] - cy, cen[2] - cz   # 트럭(lateral)은 피사체도 같이 민다
        hd = math.hypot(dx, dy)
        pitch = math.atan2(dz, hd) - off + math.radians(C.get("tilt_up", 0.0)) * tilt_e(t)
        hx, hy = (dx / hd, dy / hd) if hd > 1e-9 else (0.0, 1.0)
        aim.location = (cx + d * hx * math.cos(pitch), cy + d * hy * math.cos(pitch), cz + d * math.sin(pitch))
        cam.keyframe_insert("location", frame=f); aim.keyframe_insert("location", frame=f)
        fo = ctx.get("focus_offset", (0, 0, 0))
        cd.dof.focus_distance = math.sqrt((dx + fo[0]) ** 2 + (dy + fo[1]) ** 2 + (dz + fo[2]) ** 2)
        cd.dof.keyframe_insert("focus_distance", frame=f)
    ctx["camera"] = cam; ctx["aim"] = aim
    return cam

# ---------- 컴포지터: 흑백 → 필름 S곡선 → 비네팅 → 그레인(프레임 시드) ----------
def build_compositor(ctx):
    sc = ctx["scene"]
    ng = bpy.data.node_groups.new("comp", "CompositorNodeTree")
    ng.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    n, l = ng.nodes, ng.links
    rl = n.new("CompositorNodeRLayers"); rl.scene = sc
    hs = n.new("CompositorNodeHueSat"); hs.inputs["Saturation"].default_value = 0.0
    l.new(rl.outputs["Image"], hs.inputs["Image"])
    cv = n.new("CompositorNodeCurveRGB"); c = cv.mapping.curves[3]
    c.points[0].location = (0.0, 0.0); c.points[1].location = (1.0, 1.0)
    c.points.new(0.18, 0.10); c.points.new(0.50, 0.52); c.points.new(0.80, 0.86); cv.mapping.update()
    l.new(hs.outputs["Image"], cv.inputs["Image"])
    em = n.new("CompositorNodeEllipseMask"); em.inputs["Size"].default_value = (1.55, 1.30); em.inputs["Position"].default_value = (0.5, 0.5)
    bl = n.new("CompositorNodeBlur"); bl.inputs["Size"].default_value = (420, 420)
    try: bl.inputs["Type"].default_value = "GAUSS"
    except Exception: pass
    l.new(em.outputs["Mask"], bl.inputs["Image"])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs["Factor"].default_value = ctx["spec"].get("vignette", 0.55)
    A = [s for s in mx.inputs if s.name == "A" and s.type == "RGBA"][0]; B = [s for s in mx.inputs if s.name == "B" and s.type == "RGBA"][0]
    O = [s for s in mx.outputs if s.type == "RGBA"][0]
    l.new(cv.outputs["Image"], A); l.new(bl.outputs["Image"], B)
    # ❌ 그레인(WhiteNoise 4D · W=프레임) 제거 — 9/22 실측: 헤드리스 컴포지터에서 ImageCoordinates 가 픽셀 좌표를 안 줘
    #    프레임마다 화면 전체에 «상수 하나»를 더했다(평균 밝기 ±25 요동 · 박동균 「부들부들」). 그레인이 필요하면 Remotion 쪽 frame 시드 그레인으로.
    O2 = O
    go = n.new("NodeGroupOutput"); l.new(O2, go.inputs[0])
    sc.compositing_node_group = ng
    try: sc.render.compositor_device = "CPU"
    except Exception: pass
    sc.render.use_compositing = not ctx["args"].nocomp

# ---------- Cycles ----------
def build_engine(ctx):
    sc = ctx["scene"]; a = ctx["args"]
    sc.render.engine = "CYCLES"; cy = sc.cycles
    cy.device = "CPU"; cy.samples = a.samples; cy.use_adaptive_sampling = False; cy.seed = 7
    cy.use_denoising = True; cy.denoiser = "OPENIMAGEDENOISE"
    try: cy.denoising_use_gpu = False
    except Exception: pass
    # --gpu (9/22 · Colab T4): OPTIX → CUDA 순으로 잡히는 첫 장치를 쓴다. 디노이저는 OIDN 그대로(결과 동일성 유지 · GPU OIDN 도 허용).
    if getattr(a, "gpu", False):
        prefs = bpy.context.preferences.addons["cycles"].preferences
        picked = None
        for kind in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                devs = [d for d in prefs.devices if d.type == kind]
                if devs:
                    for d in prefs.devices: d.use = (d.type == kind)
                    picked = kind; break
            except Exception: continue
        if picked:
            cy.device = "GPU"
            try: cy.denoising_use_gpu = True
            except Exception: pass
            print(f"GPU 렌더: {picked} · {[d.name for d in prefs.devices if d.use]}")
        else:
            print("GPU 없음 — CPU 로 진행")
    cy.max_bounces = 12; cy.transmission_bounces = 12; cy.glossy_bounces = 6; cy.volume_bounces = 2; cy.transparent_max_bounces = 16
    cy.caustics_reflective = True; cy.caustics_refractive = True
    cy.volume_step_rate = 1.0; cy.volume_max_steps = 512
    sc.render.threads_mode = "AUTO"
    mb = ctx["spec"].get("motion_blur")
    if mb:
        sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = mb
        try: sc.cycles.motion_blur_position = "CENTER"
        except Exception: pass

def finalize(ctx):
    if not ctx.get("camera"): build_camera(ctx)   # 장면이 카메라를 직접 만들었으면 건너뜀 (v8)
    build_lights(ctx)
    if ctx.get("post_lights"): ctx["post_lights"](ctx)
    build_haze(ctx); build_orb(ctx); build_engine(ctx); build_compositor(ctx)
