"""Repair the right-hand bank frontage after the setback pass.

The wide 15 m SM_Bld_Shop_02 was shifted to x 20.36 to clear the bank, which left
the upper apartment stacks at x 13.0 and x 17.1 with no ground-floor shop. This
pass removes that oversized shop and places 5 m shopfronts directly under the
two stacks. Deterministic and idempotent: tagged shops are rebuilt each run.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

LAYOUT = Path("specs/city-bank-v2.json")
CITY = Path("specs/city-catalog.json")
TAG = "street_frontage"

SHOPS = (
    ("SM_Bld_Shop_01", 13.0, 0.20),
    ("SM_Bld_Shop_01", 17.1, 0.12),
)

BANK_X = 12.62
BANK_Z0 = -0.20
BANK_Z1 = 20.20


def short(prefab: str) -> str:
    return Path(prefab).stem


def main() -> int:
    data = json.loads(LAYOUT.read_text(encoding="utf-8"))
    city = json.loads(CITY.read_text(encoding="utf-8"))
    entries = city["entries"]

    by_name: dict[str, dict] = {}
    for e in entries:
        if e["name"] not in {n for n, _, _ in SHOPS}:
            continue
        b = e["bounds"]
        if b["max"][0] - b["min"][0] > 5.6:
            continue
        by_name[e["name"]] = e

    missing = [n for n, _, _ in SHOPS if n not in by_name]
    if missing:
        print("RIGHT_FRONTAGE_MISSING_CATALOG", missing)
        return 1

    removed = 0
    for room in data["rooms"]:
        kept = []
        for p in room.get("props") or []:
            name = short(p["prefab"])
            x, _, z = p["position"]
            if p.get("tag") == TAG:
                removed += 1
                continue
            # The oversized shop that was moved off its apartment stack.
            if name == "SM_Bld_Shop_02" and math.hypot(x - 20.36, z - 0.31) < 0.60:
                removed += 1
                continue
            kept.append(p)
        room["props"] = kept

    exterior = next(r for r in data["rooms"] if r["id"] == "exterior")
    added = 0
    for name, x, z in SHOPS:
        e = by_name[name]
        exterior["props"].append(
            {
                "prefab": e["path"],
                "position": [x, 0.0, z],
                "rotation": [0.0, 180.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "tag": TAG,
            }
        )
        added += 1

    fails = []
    for room in data["rooms"]:
        for p in room.get("props") or []:
            if p.get("tag") != TAG:
                continue
            name = short(p["prefab"])
            e = by_name[name]
            b = e["bounds"]
            x, _, z = p["position"]
            # yaw 180: x0 = x - max.x, x1 = x - min.x, same for z.
            x0 = x - b["max"][0]
            x1 = x - b["min"][0]
            z0 = z - b["max"][2]
            z1 = z - b["min"][2]
            if x1 > -BANK_X and x0 < BANK_X and z1 > BANK_Z0 and z0 < BANK_Z1:
                fails.append(f"{name} intrudes bank x{x0:.3f}..{x1:.3f} z{z0:.3f}..{z1:.3f}")
            print(f"RIGHT_SHOP {name} x{x0:.3f}..{x1:.3f} z{z0:.3f}..{z1:.3f}")

    if fails:
        for f in fails:
            print("RIGHT_FRONTAGE_FAIL", f)
        return 1

    LAYOUT.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"RIGHT_FRONTAGE removed={removed} added={added}")
    print("RIGHT_FRONTAGE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
