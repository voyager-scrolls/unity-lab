#!/usr/bin/env python3
"""Vision kit for the Unity bank level.

Subcommands
  check  - geometric audit of the layout JSON (bounds, floats, wall embedding)
  sheet  - contact sheet of a capture folder, optional diff against a reference

No external deps beyond Pillow (already installed).
"""
import argparse
import io
import json
import math
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageChops, ImageFont
except ImportError:  # pragma: no cover
    Image = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "specs", "heist-catalog.json")
LAYOUT = os.path.join(ROOT, "specs", "heist-bank-v3.json")

MOUNT_LIKE = (
    "Ceiling_Light", "Sprinkler", "Fire_Detector", "Camera", "Aircon",
    "AirVent", "AlarmButton", "Flag_Wall", "Sign_", "SignJewellery",
    "RopeBarrier",
)
WALL_LIKE = (
    "SM_Env_Wall_", "SM_Env_VaultDoor_Frame",
)
SKIP_FLOAT = MOUNT_LIKE + ("SM_Env_Roof", "SM_Env_Ceiling", "RopeBarrier", "SM_Env_Wall", "SM_Env_VaultDoor")


def load_catalog():
    with io.open(CATALOG, encoding="utf-8") as f:
        data = json.load(f)
    rows = data["entries"] if isinstance(data, dict) and "entries" in data else data
    out = {}
    for e in rows:
        out[e["name"]] = e
    return out


def load_layout(path=None):
    with io.open(path or LAYOUT, encoding="utf-8") as f:
        return json.load(f)


def world_aabb(entry, pos, rot_deg, scale):
    """Axis-aligned bounds of a local AABB after scale, Y-rotation and translation."""
    mn = entry["bounds"]["min"]
    mx = entry["bounds"]["max"]
    sx, sy, sz = scale
    c = math.cos(math.radians(rot_deg))
    s = math.sin(math.radians(rot_deg))
    xs, ys, zs = [], [], []
    for x in (mn[0], mx[0]):
        for y in (mn[1], mx[1]):
            for z in (mn[2], mx[2]):
                px, py, pz = x * sx, y * sy, z * sz
                rx = px * c + pz * s
                rz = -px * s + pz * c
                xs.append(rx + pos[0])
                ys.append(py + pos[1])
                zs.append(rz + pos[2])
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def overlap_xz(a, b):
    ox = min(a[3], b[3]) - max(a[0], b[0])
    oz = min(a[5], b[5]) - max(a[2], b[2])
    return ox > 0 and oz > 0


def cmd_check(args):
    cat = load_catalog()
    layout = load_layout(args.json)
    name_of = lambda p: os.path.basename(p["prefab"]).replace(".prefab", "")

    props = []  # (room, name, aabb, pos, mounted)
    missing = []
    for room in layout["rooms"]:
        rid = room["id"]
        for p in room.get("props", []):
            n = name_of(p)
            e = cat.get(n)
            if e is None:
                missing.append((rid, n))
                continue
            aabb = world_aabb(e, p["position"], p.get("rotation", [0, 0, 0])[1],
                              p.get("scale", [1, 1, 1]))
            props.append((rid, n, aabb, p["position"], bool(p.get("mounted"))))

    floors = {}
    for rid, n, aabb, pos, mounted in props:
        if n.startswith(("SM_Env_Floor", "SM_Env_Sidewalk", "SM_Env_Road")):
            floors.setdefault(rid, []).append(aabb)

    report = []
    out_of_bounds = []
    floats = []
    sunk = []
    embedded = []

    for rid, n, aabb, pos, mounted in props:
        room = next(r for r in layout["rooms"] if r["id"] == rid)
        bmin = room.get("bounds", {}).get("min") if isinstance(room.get("bounds"), dict) else None
        # room bounds are stored as a flat list in some builds
        rb = room.get("bounds")
        if isinstance(rb, dict):
            rmin, rmax = rb["min"], rb["max"]
        elif isinstance(rb, list) and len(rb) >= 6:
            rmin, rmax = rb[0:3], rb[3:6]
        else:
            rmin = rmax = None
        if rmin and rmax and not n.startswith(("SM_Env_Wall", "SM_Env_Roof", "SM_Env_Ceiling")):
            if (aabb[0] < rmin[0] - 0.6 or aabb[3] > rmax[0] + 0.6 or
                    aabb[2] < rmin[2] - 0.6 or aabb[5] > rmax[2] + 0.6):
                out_of_bounds.append((rid, n, [round(v, 2) for v in pos]))

        if aabb[1] < -0.06 and not n.startswith(("SM_Env_Floor", "SM_Env_Sidewalk", "SM_Env_Road")):
            sunk.append((rid, n, round(aabb[1], 3), [round(v, 2) for v in pos]))

        # float test: needs support within 6 cm below, unless it is a mount-like fixture
        if aabb[1] > 0.06 and not mounted and not any(k in n for k in SKIP_FLOAT):
            supported = False
            for rid2, n2, a2, pos2, _m in props:
                if a2 is aabb:
                    continue
                if abs(a2[4] - aabb[1]) <= 0.06 and overlap_xz(a2, aabb):
                    supported = True
                    break
                # contained inside a case/box volume (display deck props)
                if (a2[0] - 0.02 <= aabb[0] and aabb[3] <= a2[3] + 0.02
                        and a2[2] - 0.02 <= aabb[2] and aabb[5] <= a2[5] + 0.02
                        and a2[4] > aabb[1]):
                    supported = True
                    break
            if not supported:
                # floor directly under it?
                for fa in floors.get(rid, []):
                    if abs(fa[4] - aabb[1]) <= 0.06 and overlap_xz(fa, aabb):
                        supported = True
                        break
            if not supported:
                floats.append((rid, n, round(aabb[1], 3), [round(v, 2) for v in pos]))

    # walls: a non-wall prop whose centre sits inside a wall volume
    walls = [(n, a) for rid, n, a, pos, m in props if n.startswith(WALL_LIKE)]
    for rid, n, aabb, pos, mounted in props:
        if n.startswith(WALL_LIKE) or mounted or n.startswith(MOUNT_LIKE):
            continue
        cx = (aabb[0] + aabb[3]) / 2.0
        cz = (aabb[2] + aabb[5]) / 2.0
        for wn, wa in walls:
            if wa[0] < cx < wa[3] and wa[2] < cz < wa[5] and wa[1] < pos[1] < wa[4]:
                embedded.append((rid, n, wn, [round(v, 2) for v in pos]))
                break

    print("PROPS=%d  MISSING_CATALOG=%d" % (len(props), len(missing)))
    for rid in sorted({p[0] for p in props}):
        count = sum(1 for p in props if p[0] == rid)
        print("  %-10s %3d" % (rid, count))
    def dump(title, rows):
        print("%s=%d" % (title, len(rows)))
        for r in rows[: args.limit]:
            print("   ", r)
    dump("OUT_OF_BOUNDS", out_of_bounds)
    dump("FLOATING", floats)
    dump("SUNK", sunk)
    dump("EMBEDDED_IN_WALL", embedded)
    if missing:
        dump("MISSING_CATALOG", missing)
    return 0


def _font(size=16):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def cmd_sheet(args):
    if Image is None:
        print("Pillow missing")
        return 2
    src = args.dir
    files = sorted(f for f in os.listdir(src) if f.lower().endswith(".png"))
    if not files:
        print("no PNGs in", src)
        return 2
    imgs = [(f, Image.open(os.path.join(src, f)).convert("RGB")) for f in files]
    cols = args.cols or 3
    rows = (len(imgs) + cols - 1) // cols
    tw, th = 480, 270
    pad, label_h = 10, 22
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + label_h + pad) + pad), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    fnt = _font(15)
    diff_rows = []
    for i, (name, im) in enumerate(imgs):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = pad + r * (th + label_h + pad)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y + label_h))
        tag = name
        if args.ref and os.path.exists(os.path.join(args.ref, name)):
            ref = Image.open(os.path.join(args.ref, name)).convert("RGB").resize(im.size)
            diff = ImageChops.difference(im, ref)
            bbox = diff.getbbox()
            mean = sum(diff.convert("L").getdata()) / float(im.size[0] * im.size[1])
            tag = "%s  d=%.1f" % (name, mean)
            if mean > 2.0:
                diff_rows.append((name, round(mean, 2), bbox))
        d.text((x + 4, y + 3), tag, fill=(235, 235, 235), font=fnt)
    out = args.out or os.path.join(src, "contact_sheet.png")
    sheet.save(out)
    print("WROTE", out, sheet.size)
    if args.ref:
        print("CHANGED_VIEWS=%d" % len(diff_rows))
        for name, mean, bbox in sorted(diff_rows, key=lambda t: -t[1])[: args.limit]:
            print("   %-14s mean=%5.2f bbox=%s" % (name, mean, bbox))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--json", default=LAYOUT)
    c.add_argument("--limit", type=int, default=25)
    c.set_defaults(func=cmd_check)
    s = sub.add_parser("sheet")
    s.add_argument("dir")
    s.add_argument("--ref")
    s.add_argument("--out")
    s.add_argument("--cols", type=int, default=3)
    s.add_argument("--limit", type=int, default=12)
    s.set_defaults(func=cmd_sheet)
    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
