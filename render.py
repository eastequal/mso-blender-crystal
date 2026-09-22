# -*- coding: utf-8 -*-
"""사용: blender -b -P render.py -- --scene O --frame 15
       blender -b -P render.py -- --scene D --frames 1-30 [--samples 32] [--out DIR] [--preview] [--save_blend]
출력: {out}/{scene}/f%02d.png (기본 out = 이 폴더). 타이밍은 {out}/{scene}/_timing.json 에 누적."""
import bpy, sys, os, time, json, argparse, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--scene", required=True, help="O D R S P N T W")
ap.add_argument("--frame", type=int, default=None)
ap.add_argument("--frames", default=None, help="예 1-30 또는 1,15,30")
ap.add_argument("--samples", type=int, default=32)
ap.add_argument("--res", type=float, default=100.0)
ap.add_argument("--out", default=HERE)
ap.add_argument("--preview", action="store_true", help="res 25 · samples 8")
ap.add_argument("--nocomp", action="store_true")
ap.add_argument("--nodof", action="store_true")
ap.add_argument("--save_blend", action="store_true")
ap.add_argument("--tag", default="")
ap.add_argument("--flat", action="store_true", help="--out 을 그대로 출력 폴더로 · 파일명 f%03d")
ap.add_argument("--sub", default="", help="장면 폴더 아래 하위 폴더 (예 v2 → R/v2/)")
ap.add_argument("--skip_existing", action="store_true", help="이미 있는 프레임(>0바이트)은 건너뛴다 — 큐 재시작용")
ap.add_argument("--gpu", action="store_true", help="Cycles 를 GPU(OPTIX→CUDA 순)로 — Colab T4 등. 없으면 CPU 그대로")
args = ap.parse_args(argv)
if args.preview: args.res = 25.0; args.samples = 8
if args.frame is not None: frames = [args.frame]
elif args.frames and "-" in args.frames:
    a, b = args.frames.split("-"); frames = list(range(int(a), int(b) + 1))
elif args.frames: frames = [int(x) for x in args.frames.split(",")]
else: frames = [15]

import scene_common as C
mod = importlib.import_module(f"scene_{args.scene}")
ctx = C.setup(mod.SPEC, args)
mod.build(ctx)
C.finalize(ctx)
sc = ctx["scene"]
out_dir = args.out if args.flat else (os.path.join(args.out, args.scene, args.sub) if args.sub else os.path.join(args.out, args.scene)); os.makedirs(out_dir, exist_ok=True)
if args.save_blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, f"scene_{args.scene}.blend"))
tpath = os.path.join(out_dir, "_timing.json")
log = json.load(open(tpath, encoding="utf-8")) if os.path.exists(tpath) else {}
for f in frames:
    path = os.path.join(out_dir, (f"f{f:03d}" if args.flat else f"f{f:02d}") + f"{args.tag}.png")
    if args.skip_existing and os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"SKIP {args.scene} f{f:02d} (exists)", flush=True); continue
    sc.frame_set(f); sc.render.filepath = path
    t0 = time.time(); bpy.ops.render.render(write_still=True); dt = round(time.time() - t0, 1)
    log[(f"f{f:03d}" if args.flat else f"f{f:02d}") + args.tag] = {"sec": dt, "samples": args.samples, "res": args.res}
    print(f"RENDERED {args.scene} f{f:02d} {dt}s -> {path}", flush=True)
json.dump(log, open(tpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
