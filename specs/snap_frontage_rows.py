"""Snap the near-bank frontage rows to a clean 5 m pitch.

The right row was at 13.0 / 17.1 / 22.1 / 27.1 (4.1 m pitch after the
bank setback), and the left row at -18 / -22.1 / -27.1. That made the
ground-floor shops and the apartment stacks interpenetrate. This pass
shifts the rows after the first bay to a 5 m pitch and replaces the
oversized left SM_Bld_Shop_02 with a 5 m shopfront.
"""

from __future__ import annotations

import json
from pathlib import Path

LAYOUT = Path("specs/city-bank-v2.json")
CITY = Path("specs/city-catalog.json")
TAG = "frontage_snap"


def short(prefab: str) -> str:
    return Path(prefab).stem


def main() -> int:
    data = json.loads(LAYOUT.read_text(encoding="utf-8"))
    city = json.loads(CITY.read_text(encoding="utf-8"))
    entries = city["entries"]
    shop_path = None
    wide_shop = False
    for e in entries:
        if e["name"] == "SM_Bld_Shop_01":
            b = e["bounds"]
            if b["max"][0] - b["min"][0] <= 5.6:
                shop_path = e["path"]
        if e["name"] == "SM_Bld_Shop_02":
            b = e["bounds"]
            if b["max"][0] - b["min"][0] > 10.0:
                wide_shop = True
    if shop_path is None or not wide_shop:
        print("FRONTAGE_SNAP_BAD_CATALOG")
        return 1

    shifted = 0
    removed = 0
    for room in data["rooms"]:
        kept = []
        for p in room.get("props") or []:
            name = short(p["prefab"])
            x, _, z = p["position"]
            # The old oversized left shop; its 5 m replacement is added below.
            if name == "SM_Bld_Shop_02" and -24.0 < x < -20.0 and -2.0 < z < 2.0:
                removed += 1
                continue
            if p.get("tag") == TAG:
                kept.append(p)
                continue
            if -6.0 < z < 7.0 and name.startswith("SM_Bld_"):
                if x >= 17.0 and x < 33.0:
                    p["position"][0] = round(x + 0.9, 4)
                    shifted += 1
                elif x <= -22.0 and x > -33.0:
                    p["position"][0] = round(x - 0.9, 4)
                    shifted += 1
                elif -20.5 < x < -18.5 and name == "SM_Bld_Shop_Cover_03":
                    p["position"][0] = round(x - 0.9, 4)
                    shifted += 1
            kept.append(p)
        room["props"] = kept

    # Left 5 m shopfront under the shifted stack at -23.
    exterior = next(r for r in data["rooms"] if r["id"] == "exterior")
    has_left = any(
        short(p["prefab"]) == "SM_Bld_Shop_01" and abs(p["position"][0] + 23.0) < 0.6
        for p in exterior["props"]
    )
    added = 0
    if not has_left:
        exterior["props"].append(
            {
                "prefab": shop_path,
                "position": [-23.0, 0.0, 0.20],
                "rotation": [0.0, 180.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "tag": TAG,
            }
        )
        added = 1

    if not shifted and not removed and not added:
        print("FRONTAGE_SNAP unchanged")
        print("FRONTAGE_SNAP_OK")
        return 0

    LAYOUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"FRONTAGE_SNAP shifted={shifted} removed={removed} added={added}")
    print("FRONTAGE_SNAP_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
