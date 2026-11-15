"""Curated street de-clutter for the merged bank level.

The old global AABB solver cascaded and removed too much of the street.
This pass is deliberately removal-only: a short list of audited overlapping
props is deleted by prefab name + position. No prop is moved, so the result
is deterministic and idempotent.
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

    if not removed:
        print(f"STREET_FIX removed=0 props={before}")
        print("STREET_FIX_OK")
        return

    room["props"] = [p for p in props if id(p) not in removed]
    after = len(room["props"])
    LAYOUT.write_text(
        json.dumps(layout, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"STREET_FIX removed={len(removed)} props {before}->{after}")
    print("STREET_FIX_OK")


if __name__ == "__main__":
    main()
