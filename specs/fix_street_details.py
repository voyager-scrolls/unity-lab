"""Street detail cleanup: remove floating trash bags, clear benches from bus
stops, and restore the entrance cones that were removed during de-cluttering.
"""

from __future__ import annotations

import json
from pathlib import Path

LAYOUT = Path("specs/city-bank-v2.json")
CITY = Path("specs/city-catalog.json")
CONE_TAG = "entrance_cone"


def short(prefab: str) -> str:
    return Path(prefab).stem


def aabb(name, x, z, yaw, bounds):
    mn, mx = bounds
    if yaw == 90:
        return x - mx[2], x - mn[2], z + mn[0], z + mx[0]
    if yaw == 180:
        return x - mx[0], x - mn[0], z - mx[2], z - mn[2]
    if yaw == 270:
        return x + mn[2], x + mx[2], z - mx[0], z - mn[0]
    return x + mn[0], x + mx[0], z + mn[2], z + mx[2]


def main() -> int:
    data = json.loads(LAYOUT.read_text(encoding="utf-8"))
    city = json.loads(CITY.read_text(encoding="utf-8"))
    bounds = {}
    for e in city["entries"]:
        b = e["bounds"]
        bounds.setdefault(e["name"], (b["min"], b["max"]))
    cone_path = None
    for e in city["entries"]:
        if e["name"] == "SM_Prop_Cone_01":
            cone_path = e["path"]
            break
    if cone_path is None:
        print("STREET_DETAILS_BAD_CATALOG")
        return 1

    removed_bags = 0
    removed_benches = 0
    kept_tagged = 0
    for room in data["rooms"]:
        if room["id"] != "exterior":
            continue
        buses = []
        for p in room["props"]:
            if short(p["prefab"]) == "SM_Prop_BusStop_01":
                n = "SM_Prop_BusStop_01"
                x, _, z = p["position"]
                buses.append(aabb(n, x, z, round(p["rotation"][1]) % 360, bounds[n]))
        kept = []
        for p in room["props"]:
            n = short(p["prefab"])
            if n.startswith("SM_Prop_TrashBag_"):
                removed_bags += 1
                continue
            if p.get("tag") == CONE_TAG:
                continue
            if n == "SM_Prop_ParkBench_01":
                x, _, z = p["position"]
                bx0, bx1, bz0, bz1 = aabb(n, x, z, round(p["rotation"][1]) % 360, bounds[n])
                hit = False
                for x0, x1, z0, z1 in buses:
                    if min(bx1, x1) - max(bx0, x0) > 0.05 and min(bz1, z1) - max(bz0, z0) > 0.05:
                        hit = True
                        break
                if hit:
                    removed_benches += 1
                    continue
            kept.append(p)
        room["props"] = kept

    exterior = next(r for r in data["rooms"] if r["id"] == "exterior")
    added = 0
    for x in (-6.0, -4.5, 4.5, 6.0):
        exterior["props"].append(
            {
                "prefab": cone_path,
                "position": [x, 0.0, -11.6],
                "rotation": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "tag": CONE_TAG,
            }
        )
        added += 1

    # Idempotence: the cone count is the only expected tagged addition.
    data.setdefault("street_details", {})
    data["street_details"] = {"trash_bags_removed": removed_bags,
                              "benches_cleared": removed_benches,
                              "entrance_cones": added}

    LAYOUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"STREET_DETAILS bags_removed={removed_bags} benches_removed={removed_benches} cones_added={added}")
    print("STREET_DETAILS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
