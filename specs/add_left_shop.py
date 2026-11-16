"""Place the missing 5 m shopfront under the left apartment stack at -23."""

from __future__ import annotations

import json
from pathlib import Path

LAYOUT = Path("specs/city-bank-v2.json")
CITY = Path("specs/city-catalog.json")
TAG = "frontage_left"


def short(prefab: str) -> str:
    return Path(prefab).stem


def main() -> int:
    data = json.loads(LAYOUT.read_text(encoding="utf-8"))
    city = json.loads(CITY.read_text(encoding="utf-8"))
    path = None
    for e in city["entries"]:
        if e["name"] == "SM_Bld_Shop_01":
            b = e["bounds"]
            if b["max"][0] - b["min"][0] <= 5.6:
                path = e["path"]
                break
    if path is None:
        print("LEFT_SHOP_BAD_CATALOG")
        return 1

    exterior = next(r for r in data["rooms"] if r["id"] == "exterior")
    removed = 0
    kept = []
    for p in exterior["props"]:
        if p.get("tag") == TAG:
            removed += 1
            continue
        if short(p["prefab"]) == "SM_Bld_Shop_01" and abs(p["position"][0] + 23.0) < 0.6:
            removed += 1
            continue
        kept.append(p)
    exterior["props"] = kept
    exterior["props"].append(
        {
            "prefab": path,
            "position": [-23.0, 0.0, 0.20],
            "rotation": [0.0, 180.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
            "tag": TAG,
        }
    )
    LAYOUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"LEFT_SHOP removed={removed} added=1")
    print("LEFT_SHOP_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
