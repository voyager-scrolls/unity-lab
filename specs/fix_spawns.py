"""Place the four attacker spawns on clear perimeter points.

Old exterior spawns were clustered mid-street; two sat inside vehicles.
New spawns form a south/flank arc inside the x+-40, z -40..0 boundary:
(-32,-36), (32,-36), (-32,-18), (32,-18).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

LAYOUT = Path("specs/city-bank-v2.json")
HEIST = Path("specs/heist-catalog.json")
CITY = Path("specs/city-catalog.json")

SPAWNS = [
    {"position": [-32.0, 0.0, -36.0], "team": 1, "type": "delta"},
    {"position": [32.0, 0.0, -36.0], "team": 1, "type": "delta"},
    {"position": [-32.0, 0.0, -18.0], "team": 1, "type": "recon"},
    {"position": [32.0, 0.0, -18.0], "team": 1, "type": "recon"},
]

GROUND = ("Sidewalk", "Road", "Floor", "Ground", "Crossing", "Lines", "Plane")


def short(prefab: str) -> str:
    return Path(prefab).stem


def rot_box(name, x, z, yaw, bounds):
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
    bounds = {}
    for e in json.loads(HEIST.read_text(encoding="utf-8")):
        b = e["bounds"]
        bounds.setdefault(e["name"], (b["min"], b["max"]))
    for e in json.loads(CITY.read_text(encoding="utf-8"))["entries"]:
        b = e["bounds"]
        bounds.setdefault(e["name"], (b["min"], b["max"]))

    ext = next(r for r in data["rooms"] if r["id"] == "exterior")
    props = []
    for p in ext["props"]:
        n = short(p["prefab"])
        if n not in bounds or p["position"][1] > 1.0 or any(g in n for g in GROUND):
            continue
        x, _, z = p["position"]
        props.append((n, *rot_box(n, x, z, round(p["rotation"][1]) % 360, bounds[n])))

    fails = []
    covers = ext.get("coverPoints") or []
    for s in SPAWNS:
        x, _, z = s["position"]
        if not (-40.0 <= x <= 40.0 and -40.0 <= z <= 0.0):
            fails.append(f"outside perimeter: {s}")
        hits = [n for n, x0, x1, z0, z1 in props
                if x0 - 0.8 <= x <= x1 + 0.8 and z0 - 0.8 <= z <= z1 + 0.8]
        if hits:
            fails.append(f"prop overlap at {s}: {hits[:4]}")
        near = min((math.hypot(c["position"][0] - x, c["position"][2] - z) for c in covers), default=999)
        if near < 2.0:
            fails.append(f"cover too close ({near:.1f}) at {s}")
        print(f"SPAWN {s['position']} clear={not hits} nearest_cover={near:.1f}")

    if fails:
        for f in fails:
            print("SPAWN_FAIL", f)
        return 1

    ext["spawnPoints"] = SPAWNS
    LAYOUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("SPAWN_POINTS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
