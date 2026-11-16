"""Curated street de-clutter for the merged bank level.

The old global AABB solver cascaded and removed too much of the street.
This pass uses a short audited removal list plus deterministic orientation
fixes: duplicate benches and phone banks are deleted, remaining benches are
turned to face the street and moved off the wall. No global solver.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

LAYOUT = Path("specs/city-bank-v2.json")

# (name substring or tuple, x, z, radius)
REMOVALS = [
    # duplicate benches on the right-hand pavement
    ("ParkBench", 24.0, -2.202, 0.60),
    ("ParkBench", 34.0, -2.202, 0.60),
    ("ParkBench", 44.0, -2.202, 0.60),
    ("ParkBench", 54.0, -2.202, 0.60),
    # hydrants under trees / duplicate hydrants
    ("Hydrant", -51.0, -4.20, 0.45),
    ("Hydrant", -41.0, -4.20, 0.45),
    ("Hydrant", -31.5, -4.20, 0.45),
    ("Hydrant", -31.0, -4.20, 0.45),
    ("Hydrant", 31.5, -4.20, 0.45),
    ("Hydrant", 31.0, -4.20, 0.45),
    ("Hydrant", 41.0, -4.20, 0.45),
    ("Hydrant", 51.0, -4.20, 0.45),
    # cones clipping light poles / each other / crossing
    (("Cone_01", "Cone_02"), -29.0, -9.40, 0.60),
    (("Cone_01", "Cone_02"), -25.0, -9.20, 0.60),
    (("Cone_01", "Cone_02"), -6.0, -11.60, 0.60),
    (("Cone_01", "Cone_02"), -4.5, -11.60, 0.60),
    (("Cone_01", "Cone_02"), 4.5, -11.60, 0.60),
    (("Cone_01", "Cone_02"), 6.0, -11.60, 0.60),
    (("Cone_01", "Cone_02"), 25.0, -9.20, 0.60),
    (("Cone_01", "Cone_02"), 29.0, -9.40, 0.60),
    # bins clipping phone banks / bus stops
    (("Trash", "Bin"), -38.5, -3.20, 0.60),
    (("Trash", "Bin"), -36.0, -3.40, 0.60),
    (("Trash", "Bin"), -18.5, -3.20, 0.60),
    (("Trash", "Bin"), -17.0, -3.40, 0.60),
    (("Trash", "Bin"), 17.0, -3.40, 0.60),
    (("Trash", "Bin"), 18.5, -3.20, 0.60),
    (("Trash", "Bin"), 36.0, -3.40, 0.60),
    (("Trash", "Bin"), 38.5, -3.20, 0.60),
    # planters clipping benches / phone banks / bus stops
    ("Planter", -53.0, -2.40, 0.60),
    ("Planter", -43.0, -2.40, 0.60),
    ("Planter", -33.0, -2.40, 0.60),
    ("Planter", -23.0, -2.40, 0.60),
    ("Planter", -32.0, -3.10, 0.60),
    ("Planter", -20.0, -3.10, 0.60),
    ("Planter", 20.0, -3.10, 0.60),
    ("Planter", 32.0, -3.10, 0.60),
    # parking meters inside parked cars
    ("Meter", -42.0, -10.90, 0.55),
    ("Meter", -34.0, -10.90, 0.55),
    ("Meter", -26.0, -10.90, 0.55),
    ("Meter", 26.0, -10.90, 0.55),
    ("Meter", 34.0, -10.90, 0.55),
    ("Meter", 42.0, -10.90, 0.55),
    # crate / container / ammo clusters at the barricade line
    ("Crate_Large", -22.8, -16.30, 0.70),
    ("Crate_Large", 22.8, -16.30, 0.70),
    ("Crate_01", -25.25, -16.20, 0.70),
    ("Crate_01", 25.25, -16.20, 0.70),
    ("Container_01", -32.0, -17.2005, 0.80),
    ("Container_01", 32.0, -17.2005, 0.80),
    ("AmmoBox", -22.6, -19.60, 0.60),
    ("AmmoBox", 22.6, -19.60, 0.60),
    # duplicate benches on the left-hand pavement (mirror of the right)
    ("ParkBench", -54.05, -2.202, 0.60),
    ("ParkBench", -44.05, -2.202, 0.60),
    ("ParkBench", -34.05, -2.202, 0.60),
    ("ParkBench", -24.05, -2.202, 0.60),
    # freestanding phone banks; left one shows the black side-panel glitch
    ("Phones", -18.2, -3.60, 0.80),
    ("Phones", -33.2, -3.60, 0.80),
    ("Phones", -51.1, -3.60, 0.80),
    ("Phones", 18.2, -3.60, 0.80),
    ("Phones", 33.2, -3.60, 0.80),
    ("Phones", 51.1, -3.60, 0.80),
]


def short(prefab: str) -> str:
    return prefab.replace("\\", "/").split("/")[-1].replace(".prefab", "")


def matches(name: str, key) -> bool:
    keys = key if isinstance(key, tuple) else (key,)
    return any(k.lower() in name.lower() for k in keys)


def main() -> None:
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    room = next(r for r in layout["rooms"] if r["id"] == "exterior")
    props = room["props"]
    before = len(props)

    removed = set()
    for key, x, z, radius in REMOVALS:
        for p in props:
            if id(p) in removed:
                continue
            px, pz = p["position"][0], p["position"][2]
            if math.hypot(px - x, pz - z) > radius:
                continue
            name = short(p["prefab"])
            if not matches(name, key):
                continue
            removed.add(id(p))
            print(f"REMOVE {name} at ({px:.2f},{pz:.2f})")
            break

    room["props"] = [p for p in props if id(p) not in removed]

    # Remove the paired duplicate benches reintroduced by the street generator.
    deduped = 0
    bench_seen = []
    kept = []
    for p in room["props"]:
        if short(p["prefab"]) == "SM_Prop_ParkBench_01":
            px, pz = p["position"][0], p["position"][2]
            if any(math.hypot(px - bx, pz - bz) < 1.0 for bx, bz in bench_seen):
                deduped += 1
                print(f"REMOVE duplicate bench at ({px:.2f},{pz:.2f})")
                continue
            bench_seen.append((px, pz))
        kept.append(p)
    room["props"] = kept

    oriented = 0
    for p in room["props"]:
        n = short(p["prefab"])
        if n == "SM_Prop_ParkBench_01":
            if abs(p["rotation"][1] - 180.0) > 1e-6 or abs(p["position"][2] + 3.80) > 1e-6:
                p["rotation"][1] = 180.0
                p["position"][2] = -3.80
                oriented += 1
        elif n == "SM_Prop_BusStop_01":
            if abs(p["rotation"][1] - 180.0) > 1e-6:
                p["rotation"][1] = 180.0
                oriented += 1

    # Final duplicate pass after orientation; the generator can leave a
    # second bench 0.1 m from its pair.
    seen = []
    kept = []
    for p in room["props"]:
        if short(p["prefab"]) == "SM_Prop_ParkBench_01":
            px, pz = p["position"][0], p["position"][2]
            if any(math.hypot(px - bx, pz - bz) < 1.0 for bx, bz in seen):
                deduped += 1
                print(f"REMOVE duplicate bench at ({px:.2f},{pz:.2f})")
                continue
            seen.append((px, pz))
        kept.append(p)
    room["props"] = kept

    after = len(room["props"])
    if removed or deduped or oriented:
        LAYOUT.write_text(
            json.dumps(layout, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(f"STREET_FIX removed={len(removed)} deduped={deduped} oriented={oriented} props {before}->{after}")
    print("STREET_FIX_OK")


if __name__ == "__main__":
    main()
