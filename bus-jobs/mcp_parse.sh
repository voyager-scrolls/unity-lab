#!/bin/bash
# mcp_parse.sh — extract scene hierarchy + errors-only console from mcp_result.json
set -e
python3 - <<'PYEOF'
import json
try:
    data = json.load(open("/content/mcp_result.json"))
except Exception as e:
    print("JSON_PARSE_FAIL:", repr(e))
    raise SystemExit(1)

# The result is a batch_execute result with "results" array
results = data.get("results", [])
print("=== BATCH RESULT ===")
print("callSuccessCount:", data.get("callSuccessCount"))
print("callFailureCount:", data.get("callFailureCount"))
print()

for i, r in enumerate(results):
    tool = r.get("tool", "?")
    print(f"--- Tool {i}: {tool} ---")
    if "error" in r:
        print("ERROR:", r["error"])
        continue
    result = r.get("result", r)
    if tool == "manage_scene":
        # Print hierarchy summary: count of GOs, top-level names
        if isinstance(result, dict):
            hierarchy = result.get("hierarchy", result.get("data", result))
            if isinstance(hierarchy, list):
                print("Top-level GameObjects:", len(hierarchy))
                for go in hierarchy:
                    name = go.get("name", "?")
                    comps = go.get("components", [])
                    comp_names = [c.get("type", "?") if isinstance(c, dict) else str(c) for c in comps] if isinstance(comps, list) else []
                    print(f"  {name}  components={comp_names}")
            else:
                print(json.dumps(result, indent=2)[:4000])
        else:
            print(str(result)[:4000])
    elif tool == "read_console":
        if isinstance(result, dict):
            logs = result.get("logs", result.get("entries", result.get("data", [])))
            if isinstance(logs, list):
                errors = [l for l in logs if isinstance(l, dict) and l.get("type", "").lower() in ("error", "exception")]
                warnings = [l for l in logs if isinstance(l, dict) and l.get("type", "").lower() == "warning"]
                print(f"Total logs: {len(logs)}  Errors: {len(errors)}  Warnings: {len(warnings)}")
                print("--- ERRORS ---")
                for l in errors:
                    print("  ", l.get("message", l.get("log", str(l)))[:300])
                print("--- WARNINGS (first 10) ---")
                for l in warnings[:10]:
                    print("  ", l.get("message", l.get("log", str(l)))[:200])
            else:
                print(json.dumps(result, indent=2)[:4000])
        else:
            print(str(result)[:4000])
    else:
        print(json.dumps(result, indent=2)[:4000])
    print()
PYEOF