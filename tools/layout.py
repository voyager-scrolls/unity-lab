#!/usr/bin/env python3
"""layout.py - offline QA for heist level layouts.

Checks a layout JSON (the file the scene job consumes) against the prefab
catalogue without Unity, so structural mistakes are caught in milliseconds
instead of after a 65 s VM build.

    python tools/layout.py check specs/heist-bank-v3.json
    python tools/layout.py check specs/heist-bank-v3.json --json builds/layout-report.json
    python tools/layout.py diff old.json new.json
    python tools/layout.py budget specs/heist-bank-v3.json
"""
import argparse
import json
import math
import os
import sys

CATALOG_DEFAULT = "specs/heist-catalog.json"
PLAYER_RADIUS = 0.35
CELL = 0.25

FLOOR_HINTS = ("Floor", "Sidewalk", "Road", "Rug")
CEIL_HINTS = ("Ceiling", "Roof", "Sprinkler", "Fire_Detector")
WALL_HINTS = ("Wall_", "VaultDoor_Frame", "VaultGate_Wall")
HANG_HINTS = ("RopeBarrier_0", "Flag_Wall", "Camera", "Ceiling_Light", "AirVent", "Aircon", "Sprinkler", "Fire_Detector", "Sign_", "AlarmButton", "Flag_Straight")


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def catalog_index(cat):
    idx = {}
    entries = cat.get("entries", cat) if isinstance(cat, dict) else cat
    for e in entries:
        idx[os.path.basename(e["path"])] = e
        idx.setdefault(e["name"], e)
    return idx


def rot_y(x, z, deg):
    if deg % 360 == 0:
        return x, z
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return x * c + z * s, -x * s + z * c


def prop_box(p, idx):
    name = os.path.basename(p["prefab"])
    e = idx.get(name)
    if e is None:
        return None
    b = e["bounds"]
    mn, mx = b["min"], b["max"]
    sc = p.get("scale", [1, 1, 1])
    pts = []
    for x in (mn[0], mx[0]):
        for y in (mn[1], mx[1]):
            for z in (mn[2], mx[2]):
                rx, rz = rot_y(x * sc[0], z * sc[2], p.get("rotation", [0, 0, 0])[1])
                pts.append((rx, y * sc[1], rz))
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    zs = [q[2] for q in pts]
    pos = p["position"]
    return (min(xs) + pos[0], min(ys) + pos[1], min(zs) + pos[2],
            max(xs) + pos[0], max(ys) + pos[1], max(zs) + pos[2])


def volume(a):
    return max(0.0, a[3] - a[0]) * max(0.0, a[4] - a[1]) * max(0.0, a[5] - a[2])


def inter(a, b):
    return (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]),
            min(a[3], b[3]), min(a[4], b[4]), min(a[5], b[5]))


def overlaps_xz(a, b, pad=0.0):
    return a[0] < b[3] - pad and b[0] < a[3] - pad and a[2] < b[5] - pad and b[2] < a[5] - pad


def cls(name):
    for h in FLOOR_HINTS:
        if h in name:
            return "floor"
    for h in CEIL_HINTS:
        if h in name:
            return "ceiling"
    for h in WALL_HINTS:
        if h in name:
            return "wall"
    return "prop"


def contained(a, b):
    """a fully inside b (2 cm tolerance)"""
    return (a[0] >= b[0] - 0.02 and a[3] <= b[3] + 0.02 and
            a[1] >= b[1] - 0.02 and a[4] <= b[4] + 0.02 and
            a[2] >= b[2] - 0.02 and a[5] <= b[5] + 0.02)


def is_hanging(name):
    return any(h in name for h in HANG_HINTS)


def room_bounds(room):
    b = room.get("bounds")
    if not b:
        return None
    if isinstance(b, dict):
        return (b["min"][0], b["min"][1], b["min"][2], b["max"][0], b["max"][1], b["max"][2])
    return tuple(b)


def check(path, cat_path, out_json=None):
    layout = load(path)
    cat = load(cat_path)
    idx = catalog_index(cat)
    rooms = layout.get("rooms", [])
    problems = []      # (severity, code, message)
    stats = {"props": 0, "missing_catalog": 0, "rooms": len(rooms), "tris": 0}
    materials = set()

    records = []
    for room in rooms:
        rid = room.get("id", "?")
        rb = room_bounds(room)
        for p in room.get("props", []):
            stats["props"] += 1
            name = os.path.basename(p["prefab"])
            box = prop_box(p, idx)
            if box is None:
                stats["missing_catalog"] += 1
                problems.append(("warn", "NO_CATALOG", "%s %s" % (rid, name)))
                continue
            e = idx.get(name, {})
            stats["tris"] += int(e.get("triangles", 0) or 0)
            materials.add(str(e.get("material", "")))
            records.append({"room": rid, "name": name, "box": box, "cls": cls(name),
                            "collider": str((e.get("collider") or {}).get("type", "none")),
                            "p": p})

    # -- bounds / sink
    for r in records:
        b = r["box"]
        rb = next((room_bounds(rm) for rm in rooms if rm.get("id") == r["room"]), None)
        if r["cls"] == "ceiling":
            rb = None
        if rb and (b[3] < rb[0] or b[0] > rb[3] or b[5] < rb[2] or b[2] > rb[5] or b[4] < rb[1] - 0.01 or b[1] > rb[4] + 0.01):
            problems.append(("warn", "OUT_OF_BOUNDS", "%s %s at (%.1f,%.1f,%.1f)" % (r["room"], r["name"], r["p"]["position"][0], r["p"]["position"][1], r["p"]["position"][2])))
        if b[1] < -0.08:
            problems.append(("fail", "SUNK", "%s %s min y %.2f" % (r["room"], r["name"], b[1])))

    # -- float: needs support below (top within 0.12 m) or hanging class
    for r in records:
        if r["cls"] in ("floor", "wall", "ceiling"):
            continue
        b = r["box"]
        if b[1] <= 0.10 or is_hanging(r["name"]):
            continue
        supported = False
        for o in records:
            if o is r:
                continue
            if contained(b, o["box"]):
                supported = True
                break
            ob = o["box"]
            if abs(ob[4] - b[1]) <= 0.12 and overlaps_xz(ob, b, 0.02):
                supported = True
                break
        if not supported:
            problems.append(("fail", "FLOATING", "%s %s min y %.2f" % (r["room"], r["name"], b[1])))

    # -- overlaps between solid props (ignore support pairs and decor on top)
    solid = [r for r in records if r["cls"] == "prop" and r["collider"] != "none"]
    hits = []
    for i in range(len(solid)):
        a = solid[i]
        for j in range(i + 1, len(solid)):
            b = solid[j]
            if a["room"] != b["room"]:
                continue
            ab, bb = a["box"], b["box"]
            if not overlaps_xz(ab, bb):
                continue
            iv = inter(ab, bb)
            v = volume(iv)
            if v <= 0.0:
                continue
            small = min(volume(ab), volume(bb))
            if small <= 0:
                continue
            frac = v / small
            if contained(ab, bb) or contained(bb, ab):
                continue
            support = abs(ab[4] - bb[1]) <= 0.12 or abs(bb[4] - ab[1]) <= 0.12
            if frac > 0.35 and not support:
                hits.append((frac, a, b))
    hits.sort(key=lambda t: -t[0])
    for frac, a, b in hits[:15]:
        problems.append(("warn", "OVERLAP", "%s %.0f%% %s <-> %s at (%.1f,%.1f)" % (
            a["room"], frac * 100, a["name"], b["name"], a["p"]["position"][0], a["p"]["position"][2])))

    # -- reachability: occupancy grid per room, flood fill from spawns
    grid_stats = {}
    for room in rooms:
        rid = room.get("id", "?")
        rb = room_bounds(room)
        spawns = room.get("spawnPoints") or []
        covers = room.get("coverPoints") or []
        if not rb or not spawns:
            continue
        w = int((rb[3] - rb[0]) / CELL) + 1
        h = int((rb[5] - rb[2]) / CELL) + 1
        blocked = bytearray(w * h)

        def cell(x, z):
            ix = int((x - rb[0]) / CELL)
            iz = int((z - rb[2]) / CELL)
            return ix, iz

        for r in records:
            if r["cls"] in ("floor", "ceiling", "wall") or r["room"] != rid:
                continue
            if r["collider"] == "none":
                continue
            b = r["box"]
            if b[4] - b[1] < 0.30:      # low debris does not block a walking player
                continue
            x0 = int((b[0] - PLAYER_RADIUS - rb[0]) / CELL)
            x1 = int((b[3] + PLAYER_RADIUS - rb[0]) / CELL)
            z0 = int((b[2] - PLAYER_RADIUS - rb[2]) / CELL)
            z1 = int((b[5] + PLAYER_RADIUS - rb[2]) / CELL)
            for ix in range(max(0, x0), min(w, x1 + 1)):
                base = ix * h
                for iz in range(max(0, z0), min(h, z1 + 1)):
                    blocked[base + iz] = 1

        sx, sz = cell(spawns[0]["position"][0], spawns[0]["position"][2])
        start = sx * h + sz
        if not (0 <= start < len(blocked)) or blocked[start]:
            problems.append(("fail", "SPAWN_BLOCKED", "%s spawn at %.1f,%.1f is inside geometry" % (rid, spawns[0]["position"][0], spawns[0]["position"][2])))
            continue
        seen = bytearray(len(blocked))
        stack = [start]
        seen[start] = 1
        while stack:
            cur = stack.pop()
            ix, iz = divmod(cur, h)
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, nz = ix + dx, iz + dz
                if 0 <= nx < w and 0 <= nz < h:
                    ni = nx * h + nz
                    if not seen[ni] and not blocked[ni]:
                        seen[ni] = 1
                        stack.append(ni)
        free = w * h - sum(blocked)
        reach = sum(seen)
        grid_stats[rid] = {"cells": w * h, "free": free, "reachable": reach}
        def reachable_near(x, z, rad=3):
            # points hug their cover, so accept any reachable cell within rad cells
            cx, cz = cell(x, z)
            for dx in range(-rad, rad + 1):
                for dz in range(-rad, rad + 1):
                    nx, nz = cx + dx, cz + dz
                    if 0 <= nx < w and 0 <= nz < h and seen[nx * h + nz]:
                        return True
            return False

        for i, sp in enumerate(spawns):
            if not reachable_near(sp["position"][0], sp["position"][2], 1):
                problems.append(("fail", "SPAWN_UNREACHABLE", "%s spawn %d at %.1f,%.1f" % (rid, i, sp["position"][0], sp["position"][2])))
        for i, cp in enumerate(covers):
            if not reachable_near(cp["position"][0], cp["position"][2], 3):
                problems.append(("warn", "COVER_UNREACHABLE", "%s cover %d at %.1f,%.1f" % (rid, i, cp["position"][0], cp["position"][2])))
            # cover must sit next to something tall enough to hide behind
            near = False
            for r in records:
                if r["room"] != rid or r["cls"] != "prop" or r["collider"] == "none":
                    continue
                b = r["box"]
                if b[4] - b[1] < 0.55:
                    continue
                dx = max(b[0] - cp["position"][0], 0, cp["position"][0] - b[3])
                dz = max(b[2] - cp["position"][2], 0, cp["position"][2] - b[5])
                if math.hypot(dx, dz) <= 1.6:
                    near = True
                    break
            if not near:
                problems.append(("warn", "COVER_EXPOSED", "%s cover %d at %.1f,%.1f has no cover prop within 1.6 m" % (rid, i, cp["position"][0], cp["position"][2])))

    stats["materials"] = len([m for m in materials if m and m != "None"])
    stats["unique_prefabs"] = len({r["name"] for r in records})
    fails = [p for p in problems if p[0] == "fail"]
    warns = [p for p in problems if p[0] == "warn"]

    print("LAYOUT: %s" % path)
    print("  props=%d rooms=%d triangles=%d materials=%d unique=%d missing_catalog=%d" % (
        stats["props"], stats["rooms"], stats["tris"], stats["materials"], stats["unique_prefabs"], stats["missing_catalog"]))
    for rid, g in sorted(grid_stats.items()):
        print("  %-10s free=%d reachable=%d (%.0f%%)" % (rid, g["free"], g["reachable"], 100.0 * g["reachable"] / max(1, g["free"])))
    if not problems:
        print("  NO PROBLEMS")
    for sev, code, msg in fails + warns:
        print("  %-4s %-18s %s" % (sev.upper(), code, msg))
    print("RESULT: %s (%d fail, %d warn)" % ("FAIL" if fails else "OK", len(fails), len(warns)))

    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump({"layout": path, "stats": stats, "grid": grid_stats,
                       "problems": [{"sev": s, "code": c, "msg": m} for s, c, m in problems]}, f, indent=2)
        print("REPORT: %s" % out_json)
    return 1 if fails else 0


def diff(a_path, b_path):
    a, b = load(a_path), load(b_path)
    def flat(layout):
        out = {}
        for room in layout.get("rooms", []):
            for p in room.get("props", []):
                key = (room.get("id"), os.path.basename(p["prefab"]), round(p["position"][0], 2), round(p["position"][2], 2))
                out[key] = p
        return out
    fa, fb = flat(a), flat(b)
    added = [k for k in fb if k not in fa]
    removed = [k for k in fa if k not in fb]
    print("DIFF %s -> %s" % (a_path, b_path))
    print("  added=%d removed=%d" % (len(added), len(removed)))
    from collections import Counter
    for label, keys in (("added", added), ("removed", removed)):
        c = Counter(k[0] for k in keys)
        if c:
            print("  %s by room: %s" % (label, ", ".join("%s=%d" % kv for kv in sorted(c.items()))))
        for k in keys[:10]:
            print("    %s %s at %.1f,%.1f" % (label, k[1], k[2], k[3]))
    return 0


def budget(path):
    layout = load(path)
    rows = []
    for room in layout.get("rooms", []):
        names = [os.path.basename(p["prefab"]) for p in room.get("props", [])]
        rows.append((room.get("id", "?"), len(names), len(set(names))))
    print("BUDGET %s" % path)
    for rid, n, u in rows:
        print("  %-10s props=%3d unique=%2d" % (rid, n, u))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Offline layout QA for heist level JSON")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("layout")
    c.add_argument("--catalog", default=CATALOG_DEFAULT)
    c.add_argument("--json", dest="out")
    d = sub.add_parser("diff")
    d.add_argument("a")
    d.add_argument("b")
    b = sub.add_parser("budget")
    b.add_argument("layout")
    args = ap.parse_args(argv)
    if args.cmd == "check":
        return check(args.layout, args.catalog, args.out)
    if args.cmd == "diff":
        return diff(args.a, args.b)
    return budget(args.layout)


if __name__ == "__main__":
    sys.exit(main())
