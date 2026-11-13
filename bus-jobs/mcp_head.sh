#!/bin/bash
# mcp_head.sh — print first 3000 chars of mcp_result.json structure
python3 - <<'PYEOF'
import json
d = json.load(open("/content/mcp_result.json"))
print("TYPE:", type(d).__name__)
if isinstance(d, dict):
    print("KEYS:", list(d.keys()))
    for k in d:
        v = d[k]
        if isinstance(v, (list, dict)):
            print(f"  {k}: {type(v).__name__} len={len(v)}")
        else:
            print(f"  {k}: {repr(v)[:200]}")
elif isinstance(d, list):
    print("LEN:", len(d))
    for i, item in enumerate(d[:3]):
        print(f"  [{i}]:", type(item).__name__, str(item)[:300])
print("---RAW_FIRST_3000---")
raw = open("/content/mcp_result.json").read()
print(raw[:3000])
PYEOF