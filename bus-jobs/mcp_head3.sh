#!/bin/bash
# mcp_head3.sh — explore the data dict structure
python3 - <<'PYEOF'
import json
d = json.load(open("/content/mcp_result.json"))
data = d.get("data", {})
print("DATA KEYS:", list(data.keys()))
print()
for k in data:
    v = data[k]
    print(f"=== {k}: {type(v).__name__} ===")
    if isinstance(v, list):
        print(f"  len={len(v)}")
        for i, item in enumerate(v[:3]):
            print(f"  [{i}]: {str(item)[:500]}")
    elif isinstance(v, dict):
        print(f"  keys={list(v.keys())}")
        for kk, vv in v.items():
            print(f"    {kk}: {type(vv).__name__} {str(vv)[:300]}")
    else:
        print(f"  {repr(v)[:500]}")
    print()
PYEOF