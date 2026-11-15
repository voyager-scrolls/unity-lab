"""Dress the bank interior with the Meridian Trust, 1979 aesthetic.

Deterministic post-processor. Reads specs/city-bank-v2.json plus the Heist and
City catalogues, removes any previous aesthetic props (tag == heist_aesthetic),
adds the curated set, validates placement against rooms, spawns, cover points,
doorways and other props, and only then writes the layout.

Run: py -3 specs/dress_heist_interior.py
"""
from __future__ import annotations

import json
import math
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "specs" / "city-bank-v2.json"
HEIST = ROOT / "specs" / "heist-catalog.json"
CITY = ROOT / "specs" / "city-catalog.json"
TAG = "heist_aesthetic"
TOL = 1e-4

# room id -> (xmin, zmin, xmax, zmax, ceiling)
ROOMS = {
    "lobby": (-12.5, 0.0, 12.5, 10.0, 6.0),
    "teller": (-12.5, 10.0, 12.5, 15.0, 3.4),
    "vault": (-7.5, 15.0, 7.5, 20.0, 3.4),
    "corridorL": (-12.5, 15.0, -7.5, 20.0, 3.4),
    "corridorR": (7.5, 15.0, 12.5, 20.0, 3.4),
}

SHELL_NAMES = {
    "SM_Env_Wall_Exterior_01",
    "SM_Env_Wall_Interior_01",
    "SM_Env_VaultDoor_Frame_01",
    "SM_Env_Ceiling_01",
    "SM_Env_Ceiling_04",
    "SM_Env_Roof_05",
    "SM_Env_Floor_02",
    "SM_Env_Sidewalk_01",
    "SM_Env_Ceiling_Light_01",
    "SM_Prop_Sprinkler_01",
    "SM_Prop_Camera_01",
    "SM_Prop_Fire_Detector_01",
    "SM_Prop_AirVent_01",
    "SM_Prop_AlarmButton_01",
    "SM_Prop_Sign_Bank_01",
    "SM_Prop_Flag_Wall_01",
    "SM_Prop_Flag_Wall_02",
    "SM_Env_Pillar_Exterior_04",
    "SM_Env_Pillar_Exterior_Floor_01",
    "SM_Env_Floor_01",
    "SM_Prop_Window_01",
}
WALL_DECOR = {
    "SM_Prop_Art_01",
    "SM_Prop_Art_02",
    "SM_Prop_Art_03",
    "SM_Prop_Art_04",
    "SM_Prop_Art_05",
    "SM_Prop_Art_06",
    "SM_Prop_Art_07",
    "SM_Prop_Art_08",
    "SM_Prop_Art_09",
    "SM_Prop_Clock_01",
    "SM_Prop_Clock_02",
    "SM_Prop_WallLight_01",
    "SM_Prop_Mirror_01",
    "SM_Prop_Mirror_02",
}
RUG_NAMES = {"SM_Prop_Rug_01", "SM_Prop_Rug_02", "SM_Prop_Rug_03"}

# Base props to clear before adding the table (idempotent: absent is fine).
REMOVE_BASE = [
    ("vault", "SM_Prop_Jewellery_Rings_01", -1.20, 19.00),
    ("corridorR", "SM_Item_Briefcase_01", 9.18, 19.20),
    ("teller", "SM_Prop_Jewellery_Rings_01", -11.35, 12.15),
    ("teller", "SM_Prop_Jewellery_Ring_01", -11.20, 12.75),
    ("teller", "SM_Prop_Jewellery_04", 11.30, 12.30),
    ("teller", "SM_Prop_Jewellery_Necklace_04", 11.45, 13.00),
    ("corridorL", "SM_Prop_Desk_01", -9.7828, 16.9609),
    ("corridorL", "SM_Prop_Seat_01", -11.32, 17.00),
    ("corridorL", "SM_Prop_Folder_02", -10.40, 16.80),
    ("corridorR", "SM_Prop_Folder_03", 10.40, 16.80),
    ("corridorR", "SM_Prop_Computer_01", 10.00, 17.30),
    ("lobby", "SM_Prop_Computer_01", -5.00, 8.20),
    ("lobby", "SM_Prop_Computer_01", 0.00, 8.20),
    ("lobby", "SM_Prop_Computer_01", 5.00, 8.20),
    ("lobby", "SM_Prop_Money_Stack_01", -4.28, 8.10),
    ("lobby", "SM_Prop_Money_Stack_01", -0.72, 8.10),
    ("lobby", "SM_Prop_Money_Stack_01", 4.28, 8.10),
]


def load_catalog(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data if isinstance(data, list) else data["entries"]
    return {e["name"]: e for e in entries}


CAT: dict[str, dict] = {}
for source in (HEIST, CITY):
    for name, entry in load_catalog(source).items():
        CAT.setdefault(name, entry)


def short(prefab: str) -> str:
    return prefab.replace("\\", "/").split("/")[-1].replace(".prefab", "")


def rot_box(name: str, yaw: float):
    e = CAT[name]
    mn, mx = e["bounds"]["min"], e["bounds"]["max"]
    th = math.radians(yaw)
    c, s = math.cos(th), math.sin(th)
    pts = []
    for x in (mn[0], mx[0]):
        for z in (mn[2], mx[2]):
            rx = x * c + z * s
            rz = -x * s + z * c
            pts.append((rx, rz))
    xs = [p[0] for p in pts]
    zs = [p[1] for p in pts]
    return min(xs), max(xs), min(zs), max(zs), mn[1], mx[1]


def place(name: str, cx: float, cz: float, yaw: float, y: float) -> dict:
    e = CAT[name]
    rminx, rmaxx, rminz, rmaxz, ymin, ymax = rot_box(name, yaw)
    offx = (rminx + rmaxx) / 2.0
    offz = (rminz + rmaxz) / 2.0
    return {
        "prefab": e["path"],
        "position": [round(cx - offx, 4), round(y, 4), round(cz - offz, 4)],
        "rotation": [0.0, float(yaw), 0.0],
        "scale": [1.0, 1.0, 1.0],
        "tag": TAG,
    }


def prop_box(p: dict):
    name = short(p["prefab"])
    if name not in CAT:
        return None
    yaw = p["rotation"][1]
    rminx, rmaxx, rminz, rmaxz, ymin, ymax = rot_box(name, yaw)
    px, py, pz = p["position"]
    return (px + rminx, px + rmaxx, pz + rminz, pz + rmaxz, py + ymin, py + ymax)


def aabb_overlap(a, b):
    return (
        a[0] < b[1] - TOL
        and a[1] > b[0] + TOL
        and a[2] < b[3] - TOL
        and a[3] > b[2] + TOL
        and a[4] < b[5] - 0.001
        and a[5] > b[4] + 0.001
    )


def point_aabb_dist(px, pz, box):
    dx = max(box[0] - px, 0.0, px - box[1])
    dz = max(box[2] - pz, 0.0, pz - box[3])
    return math.hypot(dx, dz)


# (room, prefab, centre-x, centre-z, yaw, y)
PLACEMENTS = [
    # ---------------- lobby: The Cathedral of Small Money ----------------
    ("lobby", "SM_Prop_Clock_02", 0.0, 0.12, 0, 3.90),
    ("lobby", "SM_Prop_Art_01", -12.40, 3.20, 90, 2.50),
    ("lobby", "SM_Prop_Art_05", -12.40, 7.40, 90, 2.40),
    ("lobby", "SM_Prop_Art_06", -12.40, 5.50, 90, 2.20),
    ("lobby", "SM_Prop_Art_07", 12.40, 3.20, 270, 2.40),
    ("lobby", "SM_Prop_Art_03", 12.40, 7.40, 270, 2.50),
    ("lobby", "SM_Prop_Mirror_02", 12.40, 5.50, 270, 2.50),
    ("lobby", "SM_Prop_WallLight_01", -12.32, 2.00, 90, 3.20),
    ("lobby", "SM_Prop_WallLight_01", -12.32, 8.80, 90, 3.20),
    ("lobby", "SM_Prop_WallLight_01", 12.32, 2.00, 270, 3.20),
    ("lobby", "SM_Prop_WallLight_01", 12.32, 8.80, 270, 3.20),
    ("lobby", "SM_Prop_LampStanding_01", -10.90, 2.40, 0, 0.0),
    ("lobby", "SM_Prop_LampStanding_01", 10.90, 2.40, 0, 0.0),
    ("lobby", "SM_Prop_LampStanding_01", -11.80, 8.00, 0, 0.0),
    ("lobby", "SM_Prop_LampStanding_01", 11.80, 8.00, 0, 0.0),
    ("lobby", "SM_Prop_Book_Group_01", -6.20, 2.00, 0, 0.510),
    ("lobby", "SM_Prop_Book_Group_05", 6.20, 2.00, 0, 0.510),
    # velvet queue in front of the teller line, centre aisle left open
    ("lobby", "SM_Prop_RopeBarrier_Pole_01", -7.50, 6.80, 0, 0.0),
    ("lobby", "SM_Prop_RopeBarrier_Pole_01", -5.50, 6.80, 0, 0.0),
    ("lobby", "SM_Prop_RopeBarrier_Pole_01", -3.50, 6.80, 0, 0.0),
    ("lobby", "SM_Prop_RopeBarrier_Pole_01", 3.50, 6.80, 0, 0.0),
    ("lobby", "SM_Prop_RopeBarrier_Pole_01", 5.50, 6.80, 0, 0.0),
    ("lobby", "SM_Prop_RopeBarrier_Pole_01", 7.50, 6.80, 0, 0.0),
    ("lobby", "SM_Prop_RopeBarrier_01", -6.50, 6.80, 0, 0.67),
    ("lobby", "SM_Prop_RopeBarrier_01", -4.50, 6.80, 0, 0.67),
    ("lobby", "SM_Prop_RopeBarrier_01", 4.50, 6.80, 0, 0.67),
    ("lobby", "SM_Prop_RopeBarrier_01", 6.50, 6.80, 0, 0.67),
    # ---------------- teller hall: The Cages ----------------
    ("teller", "SM_Prop_TellerDesk_02", -10.30, 11.90, 180, 0.0),
    ("teller", "SM_Prop_TellerDesk_02", 10.30, 11.90, 180, 0.0),
    ("teller", "SM_Prop_TellerDesk_Barrier_01", -10.30, 11.62, 180, 1.302),
    ("teller", "SM_Prop_TellerDesk_Barrier_01", 10.30, 11.62, 180, 1.302),
    ("teller", "SM_Prop_DeskLight_01", -11.25, 12.00, 180, 1.302),
    ("teller", "SM_Prop_DeskLight_01", 11.25, 12.00, 180, 1.302),
    ("teller", "SM_Prop_Book_Group_02", -10.30, 12.22, 0, 1.302),
    ("teller", "SM_Prop_Book_Group_03", 10.30, 12.22, 180, 1.302),
    ("teller", "SM_Prop_Folder_02", -9.40, 12.18, 15, 1.302),
    ("teller", "SM_Prop_Folder_02", 9.40, 12.18, 195, 1.302),
    ("teller", "SM_Prop_Chair_02", -10.30, 12.80, 0, 0.0),
    ("teller", "SM_Prop_Chair_02", 10.30, 12.80, 0, 0.0),
    ("teller", "SM_Prop_Bookshelf_01", -6.20, 14.60, 180, 0.0),
    ("teller", "SM_Prop_Bookshelf_01", 6.20, 14.60, 180, 0.0),
    ("teller", "SM_Prop_Clock_01", -6.20, 14.90, 180, 2.60),
    ("teller", "SM_Prop_Clock_01", 6.20, 14.90, 180, 2.60),
    ("teller", "SM_Prop_Art_03", -12.40, 11.50, 90, 2.20),
    ("teller", "SM_Prop_Art_05", -12.40, 13.50, 90, 2.20),
    ("teller", "SM_Prop_Art_03", 12.40, 11.50, 270, 2.20),
    ("teller", "SM_Prop_Art_05", 12.40, 13.50, 270, 2.20),
    ("teller", "SM_Prop_Rug_03", 0.0, 12.50, 0, 0.005),
    ("teller", "SM_Prop_Jewellery_Necklace_04", -4.00, 13.00, 0, 0.0),
    ("teller", "SM_Prop_Jewellery_Rings_01", 4.00, 13.20, 20, 0.0),
    # ---------------- vault: The Meridian Ironworks, 1928 ----------------
    ("vault", "SM_Prop_SafeDepositBoxes_01", 6.9615, 17.50, 270, 0.0),
    ("vault", "SM_Prop_VaultTrolley_01", 0.0, 17.50, 0, 0.0),
    ("vault", "SM_Prop_Table_02", 0.0, 19.30, 0, 0.0),
    ("vault", "SM_Prop_Clock_02", 0.0, 19.90, 180, 2.40),
    ("vault", "SM_Prop_Art_02", -3.20, 19.90, 180, 2.40),
    ("vault", "SM_Prop_Art_05", 3.20, 19.90, 180, 2.40),
    ("vault", "SM_Prop_DeskLight_01", 1.05, 18.80, 0, 0.794),
    ("vault", "SM_Item_WalkieTalkie_01", -1.10, 19.00, 0, 0.882),
    ("vault", "SM_Prop_SafeDepositBox_Cover_01", -1.60, 17.90, 15, 0.382),
    ("vault", "SM_Prop_SafeDepositBox_Cover_02", -2.20, 18.30, 70, 0.191),
    ("vault", "SM_Prop_SafeDepositBox_Container_01", 3.40, 18.30, 0, 0.0),
    ("vault", "SM_Prop_SafeDepositBox_Container_02", 3.60, 19.40, 30, 0.0),
    ("vault", "SM_Prop_Drill_01", -2.80, 18.00, 0, 0.490),
    ("vault", "SM_Item_Crowbar_01", -1.00, 17.20, 20, 0.080),
    ("vault", "SM_Prop_Money_Stack_01", 2.00, 17.30, 0, 0.0),
    ("vault", "SM_Prop_Money_Stack_01", -2.00, 17.10, 0, 0.0),
    ("vault", "SM_Prop_Money_Stack_03", 2.60, 17.60, 0, 0.0),
    # ---------------- corridor L: The Manager's Office ----------------
    ("corridorL", "SM_Prop_Bookshelf_02", -10.20, 19.60, 180, 0.0),
    ("corridorL", "SM_Prop_Book_Group_03", -10.20, 19.55, 180, 1.026),
    ("corridorL", "SM_Prop_Clock_01", -12.39, 16.60, 90, 2.40),
    ("corridorL", "SM_Prop_Art_05", -11.50, 19.90, 180, 2.20),
    ("corridorL", "SM_Prop_LampStanding_02", -11.90, 19.00, 0, 0.0),
    ("corridorL", "SM_Prop_Phone_01", -12.15, 18.40, 90, 0.0),
    ("corridorL", "SM_Prop_Rug_03", -10.00, 17.00, 90, 0.005),
    ("corridorL", "SM_Prop_Desk_02", -9.78, 16.96, 90, 0.0),
    ("corridorL", "SM_Prop_Seat_01", -11.32, 17.00, 90, 0.0),
    ("corridorL", "SM_Prop_DeskLight_01", -9.60, 16.80, 90, 0.868),
    ("corridorL", "SM_Prop_Book_Group_01", -10.10, 17.30, 90, 0.872),
    ("corridorL", "SM_Prop_Newspaper_01", -9.40, 17.50, 90, 0.868),
    ("corridorL", "SM_Prop_Safe_01", -8.40, 18.00, 0, 0.0),
    # ---------------- corridor R: Night Watch ----------------
    ("corridorR", "SM_Prop_TVCabinet_02_Combined", 9.40, 19.50, 180, 0.0),
    ("corridorR", "SM_Prop_Television_Old_01", 9.40, 19.50, 180, 0.743),
    ("corridorR", "SM_Prop_Chair_02", 11.00, 18.80, 0, 0.0),
    ("corridorR", "SM_Item_Briefcase_01", 8.20, 18.20, 0, 0.10),
    ("corridorR", "SM_Prop_Cabinet_01", 12.15, 18.20, 270, 0.0),
    ("corridorR", "SM_Prop_Clock_02", 12.39, 16.50, 270, 2.40),
    ("corridorR", "SM_Prop_Art_03", 12.39, 19.00, 270, 2.20),
    ("corridorR", "SM_Prop_Rug_03", 10.00, 17.00, 90, 0.005),
    ("corridorR", "SM_Prop_Plant_03", 12.00, 16.20, 0, 0.0),
    ("corridorR", "SM_Prop_ToolBoard_01_Combined", 7.65, 17.50, 90, 2.40),
    ("corridorR", "SM_Prop_Television_Old_01", 10.00, 17.30, 90, 0.879),
]

# Gold and cash on the trolley/table: laid out explicitly so it reads as a haul.
for x in (-0.45, -0.15, 0.15, 0.45):
    PLACEMENTS.append(("vault", "SM_Prop_GoldBar_01", x, 17.50, 0, 1.071))
for x in (-0.70, -0.35, 0.00, 0.35, 0.70):
    PLACEMENTS.append(("vault", "SM_Prop_GoldBar_02", x, 19.30, 0, 0.794))
PLACEMENTS += [
    ("vault", "SM_Prop_Money_Stack_01", -1.15, 19.50, 15, 0.794),
    ("vault", "SM_Prop_Money_Stack_01", 1.15, 19.50, 340, 0.794),
]

# 1979 teller stations: ledgers, folders and cash, no screens at all.
for x in (-5.0, 0.0, 5.0):
    PLACEMENTS.append(("lobby", "SM_Prop_Book_Group_01", x, 8.25, 0, 1.305))
    PLACEMENTS.append(("lobby", "SM_Prop_Folder_02", x + 0.70, 8.45, 0, 1.302))
    PLACEMENTS.append(("lobby", "SM_Prop_Money_Stack_01", x - 0.70, 8.45, 0, 1.302))

DOORWAYS = [
    # x0, z0, x1, z1
    (-3.0, -1.0, 3.0, 2.5),       # entrance
    (-12.5, 9.2, -7.5, 10.8),     # lobby -> corridorL
    (7.5, 9.2, 12.5, 10.8),       # lobby -> corridorR
    (-12.5, 14.2, -7.5, 15.8),    # teller -> corridorL
    (7.5, 14.2, 12.5, 15.8),      # teller -> corridorR
    (-2.5, 14.2, 2.5, 15.8),      # vault doorway centre
]


def main() -> int:
    data = json.loads(LAYOUT.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in data["rooms"]}

    removed_tagged = 0
    for room in data["rooms"]:
        kept = []
        for p in room.get("props") or []:
            if p.get("tag") == TAG:
                removed_tagged += 1
            else:
                kept.append(p)
        room["props"] = kept

    removed_base = 0
    for room_id, name, x, z in REMOVE_BASE:
        room = by_id[room_id]
        kept = []
        for p in room["props"]:
            if short(p["prefab"]) == name and math.hypot(p["position"][0] - x, p["position"][2] - z) < 0.15:
                removed_base += 1
            else:
                kept.append(p)
        room["props"] = kept

    added = 0
    for room_id, name, cx, cz, yaw, y in PLACEMENTS:
        if name not in CAT:
            raise SystemExit(f"unknown prefab {name}")
        p = place(name, cx, cz, yaw, y)
        if name == "SM_Prop_Clock_02" and abs(cx) < 0.01 and abs(cz - 0.12) < 0.01:
            p["scale"] = [1.7, 1.7, 1.0]
        elif name == "SM_Prop_Art_06" and cx < -12.0 and abs(cz - 5.50) < 0.01:
            p["scale"] = [1.8, 1.8, 1.0]
        by_id[room_id]["props"].append(p)
        added += 1

    errors = []

    # 1. bounds and wall backing for new props
    for room_id, name, cx, cz, yaw, y in PLACEMENTS:
        room = by_id[room_id]
        x0, z0, x1, z1, _ = ROOMS[room_id]
        p = next(
            q for q in room["props"]
            if q.get("tag") == TAG and short(q["prefab"]) == name
            and abs(q["position"][0] - (cx - (rot_box(name, yaw)[0] + rot_box(name, yaw)[1]) / 2)) < 0.01
            and abs(q["position"][2] - (cz - (rot_box(name, yaw)[2] + rot_box(name, yaw)[3]) / 2)) < 0.01
            and abs(q["position"][1] - y) < 0.01
        )
        box = prop_box(p)
        if box[0] < x0 - 0.15 or box[1] > x1 + 0.15 or box[2] < z0 - 0.15 or box[3] > z1 + 0.15:
            errors.append(f"OUT_OF_ROOM {room_id} {name} box={box}")
        if name in WALL_DECOR:
            # nearest wall plane behind the item
            d = min(abs(box[0] + 12.5), abs(box[1] - 12.5), abs(box[2]), abs(box[3] - 10.0), abs(box[3] - 15.0), abs(box[3] - 20.0))
            if d > 0.30:
                errors.append(f"MOUNT_NOT_ON_WALL {room_id} {name} d={d:.3f}")

    # 2. overlap with every other prop in the room (shell and rugs excluded)
    for room in data["rooms"]:
        if room["id"] not in ROOMS:
            continue
        new_props = [p for p in room["props"] if p.get("tag") == TAG]
        for p in new_props:
            name = short(p["prefab"])
            if name in WALL_DECOR or name in RUG_NAMES:
                continue
            pb = prop_box(p)
            if pb is None:
                continue
            for q in room["props"]:
                if q is p:
                    continue
                qn = short(q["prefab"])
                if qn in SHELL_NAMES or qn in RUG_NAMES or qn in WALL_DECOR:
                    continue
                qb = prop_box(q)
                if qb is None:
                    continue
                if aabb_overlap(pb, qb):
                    errors.append(
                        f"OVERLAP {room['id']} {name}@{p['position']} with {qn}@{q['position']}"
                    )

    # 3. spawn / cover clearance (floor props only)
    for room in data["rooms"]:
        if room["id"] not in ROOMS:
            continue
        points = []
        for s in room.get("spawnPoints") or []:
            points.append(("spawn", s["position"]))
        for c in room.get("coverPoints") or []:
            points.append(("cover", c["position"]))
        for p in room["props"]:
            if p.get("tag") != TAG:
                continue
            name = short(p["prefab"])
            if name in WALL_DECOR or name in RUG_NAMES:
                continue
            box = prop_box(p)
            if box is None or box[4] > 1.5:
                continue
            for kind, pos in points:
                d = point_aabb_dist(pos[0], pos[2], box)
                if d < 0.35:
                    errors.append(f"CLEARANCE {room['id']} {name} near {kind} {pos} d={d:.3f}")

    # 4. doorways / centre aisle
    for room in data["rooms"]:
        if room["id"] not in ROOMS:
            continue
        for p in room["props"]:
            if p.get("tag") != TAG:
                continue
            name = short(p["prefab"])
            if name in WALL_DECOR or name in RUG_NAMES:
                continue
            box = prop_box(p)
            if box is None:
                continue
            for dx0, dz0, dx1, dz1 in DOORWAYS:
                if box[0] < dx1 and box[1] > dx0 and box[2] < dz1 and box[3] > dz0:
                    errors.append(f"DOORWAY {room['id']} {name}@{p['position']} blocks {dx0},{dz0}..{dx1},{dz1}")
                    break

    # 5. no duplicate new positions
    seen = set()
    for room in data["rooms"]:
        for p in room["props"]:
            if p.get("tag") != TAG:
                continue
            key = (short(p["prefab"]), tuple(p["position"]), tuple(p["rotation"]))
            if key in seen:
                errors.append(f"DUPLICATE {key}")
            seen.add(key)

    if errors:
        print(f"DRESS_ERRORS {len(errors)}")
        for e in errors[:40]:
            print(" ", e)
        return 1

    LAYOUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    digest = hashlib.sha256(LAYOUT.read_bytes()).hexdigest().upper()
    print(f"removed_tagged={removed_tagged} removed_base={removed_base} added={added}")
    for rid in ROOMS:
        room = by_id[rid]
        tagged = sum(1 for p in room["props"] if p.get("tag") == TAG)
        print(f"  {rid:9s} total={len(room['props']):3d} aesthetic={tagged:2d}")
    print(f"total_props={sum(len(r['props']) for r in data['rooms'])}")
    print(f"SHA256={digest}")
    print("HEIST_DRESS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
