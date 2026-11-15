#!/usr/bin/env python3
"""Deterministic rebuild of the city-bank interior shell.

Post-processes specs/city-bank-v2.json:
  - strips every wall / vault-frame / ceiling / low roof prop inside the bank
  - rebuilds one solid perimeter (4 courses to 12 m), interior partitions, vault doorway
  - rebuilds exactly one ceiling layer per room
  - moves ceiling fixtures onto the new ceiling planes and lights both corridors

Writes only when every validation gate passes. Never hand-edit the JSON.

Run: py -3 specs/rebuild_interior_shell.py
"""

import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYOUT = os.path.join(ROOT, "specs", "city-bank-v2.json")
CATALOG = os.path.join(ROOT, "specs", "heist-catalog.json")

W_EXT = "SM_Env_Wall_Exterior_01"
W_INT = "SM_Env_Wall_Interior_01"
FRAME = "SM_Env_VaultDoor_Frame_01"
CEIL = "SM_Env_Ceiling_01"
CEIL4 = "SM_Env_Ceiling_04"
ROOF = "SM_Env_Roof_05"
LIGHT = "SM_Env_Ceiling_Light_01"

ENVELOPE = (-13.0, 13.0, -0.5, 20.5)  # xmin,xmax,zmin,zmax
TOL = 1e-4

ROOM_BOUNDS = {
    "lobby": (-12.5, 12.5, 0.0, 10.0, 6.0),
    "teller": (-12.5, 12.5, 10.0, 15.0, 3.4),
    "vault": (-7.5, 7.5, 15.0, 20.0, 3.4),
    "corridorL": (-12.5, -7.5, 15.0, 20.0, 3.4),
    "corridorR": (7.5, 12.5, 15.0, 20.0, 3.4),
}

YAW = (0, 90, 180, 270)


def short(prefab):
    return prefab.replace("\\", "/").rsplit("/", 1)[-1].replace(".prefab", "")


def rotated_rect(bmin, bmax, yaw):
    """Local AABB corners rotated by yaw, returned as min/max."""
    pts = []
    for x in (bmin[0], bmax[0]):
        for z in (bmin[2], bmax[2]):
            if yaw == 0:
                pts.append((x, z))
            elif yaw == 90:
                pts.append((z, -x))
            elif yaw == 180:
                pts.append((-x, -z))
            else:
                pts.append((-z, x))
    xs = [p[0] for p in pts]
    zs = [p[1] for p in pts]
    return min(xs), max(xs), min(zs), max(zs)


class Catalog:
    def __init__(self, path):
        data = json.load(open(path, encoding="utf-8"))
        self.by_name = {e["name"]: e for e in data}

    def bounds(self, name):
        e = self.by_name.get(name)
        if e is None:
            raise KeyError("catalog missing " + name)
        b = e["bounds"]
        return b["min"], b["max"]

    def place_center(self, name, cx, cz, yaw, y):
        """Emit a prop whose rotated footprint centre is (cx,cz), pivot height y."""
        assert yaw in YAW
        bmin, bmax = self.bounds(name)
        rx0, rx1, rz0, rz1 = rotated_rect(bmin, bmax, yaw)
        offx = (rx0 + rx1) * 0.5
        offz = (rz0 + rz1) * 0.5
        return {
            "prefab": self.by_name[name]["path"],
            "position": [round(cx - offx, 4), round(y, 4), round(cz - offz, 4)],
            "rotation": [0.0, float(yaw), 0.0],
            "scale": [1.0, 1.0, 1.0],
        }


def rect_of(cat, prop):
    name = short(prop["prefab"])
    yaw = int(round(prop["rotation"][1])) % 360
    bmin, bmax = cat.bounds(name)
    rx0, rx1, rz0, rz1 = rotated_rect(bmin, bmax, yaw)
    px, _, pz = prop["position"]
    return (px + rx0, px + rx1, pz + rz0, pz + rz1)


def inside_envelope(prop):
    x, _, z = prop["position"]
    return ENVELOPE[0] <= x <= ENVELOPE[1] and ENVELOPE[2] <= z <= ENVELOPE[3]


def near(a, b):
    return abs(a - b) <= TOL


def build(cat):
    """Return (new_props_by_room, shell_list)."""
    props = {rid: [] for rid in ("exterior", "lobby", "teller", "vault", "corridorL", "corridorR")}
    shell = []  # (room, name, prop, purpose)

    def add(room, name, cx, cz, yaw, y, purpose):
        p = cat.place_center(name, cx, cz, yaw, y)
        props[room].append(p)
        shell.append((room, name, p, purpose))
        return p

    # ---- perimeter: 4 courses to 12 m, so the sign, top window row, pilasters
    # and high roof all sit on solid wall instead of floating over the street ----
    facade_x = [-10.0, -5.0, 0.0, 5.0, 10.0]
    for course in (0, 1, 2, 3):
        y = course * 3.0
        for cx in facade_x:
            if course == 0 and cx == 0.0:
                continue  # 5 m entrance
            add("exterior", W_EXT, cx, 0.0, 0, y, "facade")
        for cz in (2.5, 7.5, 12.5, 17.5):
            add("exterior", W_EXT, -12.5, cz, 90, y, "side_left")
            add("exterior", W_EXT, 12.5, cz, 270, y, "side_right")
        for cx in (-10.0, -5.0, 0.0, 5.0, 10.0):
            add("exterior", W_EXT, cx, 20.0, 180, y, "back")

    # ---- lobby/teller partition z=10: solid centre 15 m, 5 m passages at both ends ----
    for cx in (-5.0, 0.0, 5.0):
        add("teller", W_INT, cx, 10.0, 0, 0.0, "partition_z10_low")
    for cx in (-10.0, -5.0, 0.0, 5.0, 10.0):
        add("teller", W_INT, cx, 10.0, 0, 3.0, "partition_z10_high")

    # ---- teller/vault partition z=15: solid either side of the vault doorway ----
    for cx in (-5.0, 5.0):
        add("teller", W_INT, cx, 15.0, 0, 0.0, "partition_z15")
    wall_bmin, wall_bmax = cat.bounds(W_INT)
    frame_bmin, frame_bmax = cat.bounds(FRAME)
    wall_face_z = 15.0 - (wall_bmax[2] - wall_bmin[2]) * 0.5
    frame_center_z = wall_face_z + (frame_bmax[2] - frame_bmin[2]) * 0.5
    add("teller", FRAME, 0.0, frame_center_z, 0, 0.0, "vault_frame")

    # ---- vault side walls close the vault off from both corridors ----
    add("vault", W_INT, -7.5, 17.5, 90, 0.0, "vault_side_left")
    add("vault", W_INT, 7.5, 17.5, 270, 0.0, "vault_side_right")

    # ---- single-layer ceilings (Ceiling_01 only) ----
    for cx in (-10.0, -5.0, 0.0, 5.0, 10.0):
        for cz in (2.5, 7.5):
            add("lobby", CEIL, cx, cz, 0, 6.0, "ceiling_lobby")
    for cx in (-10.0, -5.0, 0.0, 5.0, 10.0):
        add("teller", CEIL, cx, 12.5, 0, 3.4, "ceiling_teller")
    for cx in (-5.0, 0.0, 5.0):
        add("vault", CEIL, cx, 17.5, 0, 3.4, "ceiling_vault")
    add("corridorL", CEIL, -10.0, 17.5, 0, 3.4, "ceiling_corridorL")
    add("corridorR", CEIL, 10.0, 17.5, 0, 3.4, "ceiling_corridorR")

    # ---- one deterministic light set on the new ceiling planes ----
    for cx in (-8.0, 0.0, 8.0):
        for cz in (3.0, 7.0):
            add("lobby", LIGHT, cx, cz, 0, 5.99, "light_lobby")
    for cx in (-8.0, 0.0, 8.0):
        add("teller", LIGHT, cx, 12.5, 0, 3.39, "light_teller")
    for cx in (-3.5, 3.5):
        add("vault", LIGHT, cx, 17.5, 0, 3.39, "light_vault")
    add("corridorL", LIGHT, -10.0, 17.5, 0, 3.39, "light_corridorL")
    add("corridorR", LIGHT, 10.0, 17.5, 0, 3.39, "light_corridorR")

    # ---- flat roof cap over the whole footprint: closes the open top seen from
    # high angles. Sits 5 cm below the front overhang so the approved fascia edge
    # stays on top and the two slabs never z-fight. ----
    for cx in (-10.0, -5.0, 0.0, 5.0, 10.0):
        for cz in (2.5, 7.5, 12.5, 17.5):
            add("exterior", ROOF, cx, cz, 0, 11.90, "roof_cap")

    return props, shell


def validate(layout, cat, props, shell):
    fails = []
    rooms = {r["id"]: r for r in layout["rooms"]}

    # (a) perimeter wall planes: every sample must be backed by a wall module
    def wall_at(x, z, y):
        for _, name, p, _purpose in shell:
            if name not in (W_EXT, W_INT, FRAME):
                continue
            x0, x1, z0, z1 = rect_of(cat, p)
            py = p["position"][1]
            h = 3.0
            if x0 - TOL <= x <= x1 + TOL and z0 - TOL <= z <= z1 + TOL and py - TOL <= y <= py + h + TOL:
                return True
        return False

    def sweep(label, fixed, axis, lo, hi, heights, exempt=None):
        step = 0.25
        n = int(round((hi - lo) / step))
        for i in range(n + 1):
            t = lo + i * step
            for y in heights:
                if exempt and exempt(t, y):
                    continue
                x, z = (t, fixed) if axis == "x" else (fixed, t)
                if not wall_at(x, z, y):
                    fails.append("%s gap at %s=%.2f y=%.1f" % (label, axis, t, y))

    sweep("facade", 0.0, "x", -12.5, 12.5, (0.5, 1.5, 2.5, 4.5, 5.5, 7.5, 8.5, 10.5, 11.5),
          exempt=lambda t, y: y < 3.0 and abs(t) < 2.49)
    sweep("side_left", -12.5, "z", 0.0, 20.0, (0.5, 1.5, 2.5, 4.5, 5.5, 7.5, 8.5, 10.5, 11.5))
    sweep("side_right", 12.5, "z", 0.0, 20.0, (0.5, 1.5, 2.5, 4.5, 5.5, 7.5, 8.5, 10.5, 11.5))
    sweep("back", 20.0, "x", -12.5, 12.5, (0.5, 1.5, 2.5, 4.5, 5.5, 7.5, 8.5, 10.5, 11.5))

    # (b) interior partitions
    sweep("partition_z10_low", 10.0, "x", -12.5, 12.5, (0.5, 1.5, 2.5),
          exempt=lambda t, y: abs(t) > 7.51)
    sweep("partition_z10_high", 10.0, "x", -12.5, 12.5, (4.5, 5.5))
    sweep("partition_z15", 15.0, "x", -12.5, 12.5, (0.5, 1.5, 2.5),
          exempt=lambda t, y: abs(t) > 2.51)

    # (c) exactly one ceiling tile per room sample, tiles inside room bounds
    wall_bmin, wall_bmax = cat.bounds(W_INT)
    wall_face_z = 15.0 - (wall_bmax[2] - wall_bmin[2]) * 0.5
    for rid, (x0, x1, z0, z1, cy) in ROOM_BOUNDS.items():
        tiles = []
        for _, name, p, _ in shell:
            if name != CEIL or not near(p["position"][1], cy):
                continue
            rx0, rx1, rz0, rz1 = rect_of(cat, p)
            if x0 - TOL <= rx0 and rx1 <= x1 + TOL and z0 - TOL <= rz0 and rz1 <= z1 + TOL:
                tiles.append(p)
        step = 0.25
        nx = int(round((x1 - x0) / step))
        nz = int(round((z1 - z0) / step))
        for ix in range(nx):
            x = x0 + (ix + 0.5) * step
            for iz in range(nz):
                z = z0 + (iz + 0.5) * step
                hits = 0
                for _, name, p, _ in shell:
                    if name != CEIL or not near(p["position"][1], cy):
                        continue
                    rx0, rx1, rz0, rz1 = rect_of(cat, p)
                    if rx0 - TOL <= x <= rx1 + TOL and rz0 - TOL <= z <= rz1 + TOL:
                        hits += 1
                if hits != 1:
                    fails.append("ceiling %s at (%.2f,%.2f) has %d tiles" % (rid, x, z, hits))
                    break
            else:
                continue
            break
        expected = int(round((x1 - x0) / 5.0)) * int(round((z1 - z0) / 5.0))
        if len(tiles) != expected:
            fails.append("ceiling %s has %d tiles, expected %d" % (rid, len(tiles), expected))
        print("CEILING_ROOM %s tiles=%d expected=%d y=%.2f" % (rid, len(tiles), expected, cy))

    ceiling_tiles = [p for _, name, p, _ in shell if name == CEIL]
    for p in ceiling_tiles:
        rx0, rx1, rz0, rz1 = rect_of(cat, p)
        owners = []
        for rid, (x0, x1, z0, z1, cy) in ROOM_BOUNDS.items():
            if (near(p["position"][1], cy) and x0 - TOL <= rx0 and rx1 <= x1 + TOL
                    and z0 - TOL <= rz0 and rz1 <= z1 + TOL):
                owners.append(rid)
        if len(owners) != 1:
            fails.append("ceiling tile %s owned by %s" % (p["position"], owners))
    print("CEILING_TOTAL %d" % len(ceiling_tiles))

    # (c2) roof cap closes the top: exactly one tile over every footprint sample
    cap = [p for _, name, p, purpose in shell if purpose == "roof_cap"]
    if len(cap) != 20:
        fails.append("roof cap has %d tiles, expected 20" % len(cap))
    for ix in range(int(round(25.0 / 0.5))):
        x = -12.5 + (ix + 0.5) * 0.5
        for iz in range(int(round(20.0 / 0.5))):
            z = 0.0 + (iz + 0.5) * 0.5
            hits = 0
            for p in cap:
                rx0, rx1, rz0, rz1 = rect_of(cat, p)
                if rx0 - TOL <= x <= rx1 + TOL and rz0 - TOL <= z <= rz1 + TOL:
                    hits += 1
            if hits != 1:
                fails.append("roof cap at (%.2f,%.2f) has %d tiles" % (x, z, hits))
                break
        else:
            continue
        break
    print("ROOF_CAP_TILES %d" % len(cap))

    # (d) vault doorway clear, frame centred and flush with the wall face
    frame = next((p for _, name, p, purpose in shell if purpose == "vault_frame"), None)
    if frame is None:
        fails.append("vault frame missing")
    else:
        fx0, fx1, fz0, fz1 = rect_of(cat, frame)
        if not (near(fx0, -2.5) and near(fx1, 2.5)):
            fails.append("vault frame not centred: x %.3f..%.3f" % (fx0, fx1))
        if not near(fz0, wall_face_z):
            fails.append("vault frame face not flush: z0=%.4f wall=%.4f" % (fz0, wall_face_z))
    for _, name, p, purpose in shell:
        if name == FRAME or purpose.startswith("ceiling") or purpose == "vault_frame":
            continue
        x0, x1, z0, z1 = rect_of(cat, p)
        if z0 < 15.1 and z1 > 14.9 and x1 > -2.5 + TOL and x0 < 2.5 - TOL and p["position"][1] < 3.0:
            fails.append("wall module intrudes into vault doorway: %s %s" % (name, p["position"]))

    # (e) exterior wall modules must only be the perimeter
    allowed = set()
    for _, name, p, purpose in shell:
        if name == W_EXT:
            allowed.add((round(p["position"][0], 3), round(p["position"][1], 3),
                         round(p["position"][2], 3), round(p["rotation"][1], 3)))
    for rid, room in rooms.items():
        for p in room.get("props") or []:
            if short(p["prefab"]) == W_EXT:
                key = (round(p["position"][0], 3), round(p["position"][1], 3),
                       round(p["position"][2], 3), round(p["rotation"][1], 3))
                if key not in allowed:
                    fails.append("interior %s uses exterior wall at %s" % (rid, p["position"]))

    # (f) duplicate shell placements
    seen = {}
    for rid, name, p, purpose in shell:
        key = (name, round(p["position"][0], 3), round(p["position"][1], 3),
               round(p["position"][2], 3), round(p["rotation"][1], 3))
        if key in seen:
            fails.append("duplicate shell prop %s at %s" % (name, p["position"]))
        seen[key] = purpose

    # (g) counts
    counts = {}
    for _, name, _p, purpose in shell:
        counts[purpose] = counts.get(purpose, 0) + 1
    for k in sorted(counts):
        print("SHELL_COUNT %s=%d" % (k, counts[k]))
    print("SHELL_TOTAL %d" % len(shell))
    return fails


def main():
    layout = json.load(open(LAYOUT, encoding="utf-8"))
    cat = Catalog(CATALOG)

    removed = {}
    kept = {}
    for room in layout["rooms"]:
        rid = room["id"]
        out = []
        for p in room.get("props") or []:
            name = short(p["prefab"])
            x, y, z = p["position"]
            in_bank = ENVELOPE[0] <= x <= ENVELOPE[1] and ENVELOPE[2] <= z <= ENVELOPE[3]
            drop = False
            if in_bank and y < 13.0:
                if name in (W_EXT, W_INT, FRAME):
                    drop = True
                elif name in (CEIL, CEIL4) and y < 7.0:
                    drop = True
                elif name == LIGHT and 2.5 < y < 7.0:
                    drop = True
                elif name == ROOF and 5.5 <= y <= 7.5 and z > 0.5:
                    drop = True
                elif name == ROOF and 11.5 <= y <= 12.5 and z > 3.0:
                    drop = True  # roof cap rows; the z=2.15 front overhang stays
            if drop:
                removed[name] = removed.get(name, 0) + 1
            else:
                out.append(p)
                kept[name] = kept.get(name, 0) + 1
        room["props"] = out

    print("REMOVED " + " ".join("%s=%d" % (k, removed[k]) for k in sorted(removed)))
    print("BEFORE_PROPS %d" % sum(len(r.get("props") or []) for r in layout["rooms"]))

    new_props, shell = build(cat)
    for rid, plist in new_props.items():
        room = next((r for r in layout["rooms"] if r["id"] == rid), None)
        if room is None:
            raise SystemExit("layout has no room " + rid)
        room.setdefault("props", []).extend(plist)

    # ceiling-mounted fixtures follow the new rear ceiling plane
    ceiling_fixtures = ("SM_Prop_Sprinkler_01", "SM_Prop_Camera_01", "SM_Prop_Fire_Detector_01")
    for room in layout["rooms"]:
        if room["id"] not in ("teller", "vault", "corridorL", "corridorR"):
            continue
        for p in room.get("props") or []:
            if short(p["prefab"]) in ceiling_fixtures and 2.5 < p["position"][1] < 3.4:
                p["position"][1] = 3.4

    fails = validate(layout, cat, new_props, shell)
    if fails:
        print("SHELL_REBUILD_FAILED %d" % len(fails))
        for f in fails[:40]:
            print("FAIL " + f)
        sys.exit(1)

    tmp = LAYOUT + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(layout, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, LAYOUT)

    after = sum(len(r.get("props") or []) for r in layout["rooms"])
    for room in layout["rooms"]:
        print("ROOM %s props=%d" % (room["id"], len(room.get("props") or [])))
    print("AFTER_PROPS %d" % after)
    print("SHELL_REBUILD_OK")


if __name__ == "__main__":
    main()
