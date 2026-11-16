"""Remove city buildings that interpenetrate the landmark towers.

The skyline was built by layering tenements over the OfficeSquare/Octagon
landmarks, leaving many 5 m buildings buried inside the big towers. This
pass removes the buried small ground-floor buildings and the redundant
OfficeSquare_03 copies above z=20, while keeping one landmark per side.
"""

from __future__ import annotations

import json
from pathlib import Path

LAYOUT = Path("specs/city-bank-v2.json")
CITY = Path("specs/city-catalog.json")


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

    removed = 0
    removed_names = []
    for room in data["rooms"]:
        kept = []
        for p in room.get("props") or []:
            n = short(p["prefab"])
            x, y, z = p["position"]
            if n == "SM_Bld_OfficeSquare_03" and z > 20.0:
                removed += 1
                removed_names.append(f"{n}@({x:.1f},{z:.1f})")
                continue
            kept.append(p)
        room["props"] = kept

    # Ground-floor footprint pass: drop small buildings buried in big ones.
    for room in data["rooms"]:
        props = [p for p in room.get("props") or []
                 if short(p["prefab"]).startswith("SM_Bld_") and p["position"][1] < 1.0]
        shapes = []
        for p in props:
            n = short(p["prefab"])
            if n not in bounds:
                continue
            x, _, z = p["position"]
            yaw = round(p["rotation"][1]) % 360
            if yaw % 90:
                continue
            x0, x1, z0, z1 = aabb(n, x, z, yaw, bounds[n])
            area = max(0.0, x1 - x0) * max(0.0, z1 - z0)
            shapes.append((p, n, x, z, x0, x1, z0, z1, area))

        drop = set()
        for i, small in enumerate(shapes):
            p, n, x, z, x0, x1, z0, z1, area = small
            if area >= 80.0:
                continue
            for big in shapes:
                if big is small or big[8] <= 150.0:
                    continue
                ox = min(x1, big[5]) - max(x0, big[4])
                oz = min(z1, big[7]) - max(z0, big[6])
                if ox <= 0.1 or oz <= 0.1:
                    continue
                overlap = ox * oz
                if overlap >= 5.0 and overlap >= area * 0.45:
                    drop.add(id(p))
                    removed_names.append(f"{n}@({x:.1f},{z:.1f}) buried")
                    break
        if drop:
            room["props"] = [p for p in room["props"] if id(p) not in drop]
            removed += len(drop)

    if not removed:
        print("CITY_CLEAN unchanged")
        print("CITY_CLEAN_OK")
        return 0

    LAYOUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"CITY_CLEAN removed={removed}")
    for name in removed_names[:40]:
        print("REMOVE", name)
    print("CITY_CLEAN_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
