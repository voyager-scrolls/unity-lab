"""calib.py - single-image camera calibration for turning a 2D reference into metres.

Model: pinhole camera over a flat ground plane, no roll.
  horizon row  y_h  (the vanishing line of the ground plane)
  focal        f    (pixels, from the chosen horizontal FOV)
  height       h    (metres, solved from one known ground width)

Ground-plane mapping (Z = depth from camera, X = lateral, +right):
  Z = f * h / (v - y_h)
  X = (u - cx) * Z / f
This holds for a level or pitched camera as long as y_h is the true horizon row.

Subcommands
  solve  <img> --horizon ROW --ref u1,v1;u2,v2 --width W [--hfov 60] [--cx auto] [--out calib.json]
  point  --calib calib.json --u U --v V
  grid   <img> <out> --calib calib.json [--range 45] [--step 2]

Example
  py -3 tools/calib.py solve ref.jpg --horizon 640 --ref 470,900;810,900 --width 5.0 --hfov 60 --out builds/ref/calib.json
  py -3 tools/calib.py grid ref.jpg builds/ref/grid.png --calib builds/ref/calib.json --range 45 --step 2
"""

import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw


def solve(img, horizon, ref, width, hfov, cx=None):
    im = Image.open(img)
    w, h = im.size
    (u1, v1), (u2, v2) = ref
    du = abs(u2 - u1)
    if du < 4:
        raise SystemExit("reference points are too close in x (du=%d)" % du)
    f = (w * 0.5) / math.tan(math.radians(hfov) * 0.5)
    cam_h = width * ((v1 + v2) * 0.5 - horizon) / du
    if cam_h <= 0:
        raise SystemExit("reference points are above the horizon; pick points on the ground below it")
    cx_px = w * 0.5 if cx is None else cx
    print("focal      f = %.1f px  (hfov %.1f deg over %d px)" % (f, hfov, w))
    print("camera     h = %.2f m" % cam_h)
    print("horizon    y = %d px  (%.1f%% down the frame)" % (horizon, 100.0 * horizon / h))
    print("principal  cx = %.1f px" % cx_px)
    if not (1.0 <= cam_h <= 6.0):
        print("WARN  camera height outside 1-6 m: reference width or horizon row is probably off")
    return {
        "img": os.path.abspath(img),
        "width": w,
        "height": h,
        "horizon_row": horizon,
        "cx_px": cx_px,
        "hfov_deg": hfov,
        "f_px": f,
        "h_m": cam_h,
        "ref_width_m": width,
        "ref_px": [u1, v1, u2, v2],
    }


def load(path):
    with open(path, "r") as fh:
        return json.load(fh)


def to_world(c, u, v):
    dz = v - c["horizon_row"]
    if dz <= 0.5:
        return None
    f, h = c["f_px"], c["h_m"]
    Z = f * h / dz
    X = (u - c["cx_px"]) * Z / f
    return X, Z


def cmd_solve(a):
    ref = []
    for part in a.ref.split(";"):
        u, v = [float(x) for x in part.split(",")]
        ref.append((u, v))
    if len(ref) != 2:
        raise SystemExit('--ref wants "u1,v1;u2,v2"')
    c = solve(a.img, a.horizon, ref, a.width, a.hfov, a.cx if a.cx else None)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        with open(a.out, "w") as fh:
            json.dump(c, fh, indent=2)
        print("wrote", a.out)


def cmd_point(a):
    c = load(a.calib)
    r = to_world(c, a.u, a.v)
    if r is None:
        raise SystemExit("point is on or above the horizon (no ground intersection)")
    X, Z = r
    print("world  X=%.2f m  Z=%.2f m  (distance %.2f m)" % (X, Z, math.hypot(X, Z)))
    print("pixel  u=%d v=%d -> ground point" % (a.u, a.v))


def cmd_grid(a):
    c = load(a.calib)
    im = Image.open(a.img).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    w, h = im.size
    y_h = c["horizon_row"]
    f, ch, cx = c["f_px"], c["h_m"], c["cx_px"]
    # horizon
    d.line([(0, y_h), (w, y_h)], fill=(255, 0, 0, 220), width=2)
    # depth lines
    Z = a.step
    while Z <= a.range:
        v = y_h + f * ch / Z
        if 0 <= v <= h:
            d.line([(0, v), (w, v)], fill=(0, 200, 255, 120), width=1)
            d.text((6, v + 2), "%dm" % Z, fill=(0, 220, 255))
        Z += a.step
    # lateral lines
    X = -a.range
    while X <= a.range:
        pts = []
        Z2 = 1.0 / 60.0 * max(1.0, a.range / 20.0)
        Z2 = 1.0
        while Z2 <= a.range:
            u = cx + f * X / Z2
            v = y_h + f * ch / Z2
            if -50 <= u <= w + 50:
                pts.append((u, v))
            Z2 *= 1.08
        if len(pts) > 1:
            d.line(pts, fill=(255, 200, 0, 90), width=1)
        X += a.step
    # camera footprint
    d.ellipse([cx - 3, h - 6, cx + 3, h], fill=(255, 80, 80, 255))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    im.save(a.out)
    print("wrote %s  grid 1 step=%dm range=%dm  horizon=%dpx  f=%.0fpx  h=%.2fm"
          % (a.out, a.step, a.range, y_h, f, ch))


def main(argv):
    p = argparse.ArgumentParser(description="single-image camera calibration")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("solve")
    s.add_argument("img"); s.add_argument("--horizon", type=int, required=True)
    s.add_argument("--ref", required=True); s.add_argument("--width", type=float, required=True)
    s.add_argument("--hfov", type=float, default=60.0); s.add_argument("--cx", type=float, default=0.0)
    s.add_argument("--out")
    s.set_defaults(fn=cmd_solve)

    s = sub.add_parser("point")
    s.add_argument("--calib", required=True); s.add_argument("--u", type=float, required=True); s.add_argument("--v", type=float, required=True)
    s.set_defaults(fn=cmd_point)

    s = sub.add_parser("grid")
    s.add_argument("img"); s.add_argument("out"); s.add_argument("--calib", required=True)
    s.add_argument("--range", type=float, default=45.0); s.add_argument("--step", type=float, default=2.0)
    s.set_defaults(fn=cmd_grid)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main(sys.argv[1:])
