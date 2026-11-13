#!/bin/bash
# mcp_head2.sh — write parsed summary to /content/mcp_summary.txt, then cat it
python3 - <<'PYEOF'
import json
d = json.load(open("/content/mcp_result.json"))
out = []
out.append("TYPE: " + type(d).__name__)
if isinstance(d, dict):
    out.append("KEYS: " + str(list(d.keys())))
    for k in d:
        v = d[k]
        if isinstance(v, (list, dict)):
            out.append(f"  {k}: {type(v).__name__} len={len(v)}")
        else:
            out.append(f"  {k}: {repr(v)[:200]}")
elif isinstance(d, list):
    out.append("LEN: " + str(len(d)))
    for i, item in enumerate(d[:3]):
        out.append(f"  [{i}]: {type(item).__name__} {str(item)[:300]}")
# Now extract manage_scene result
out.append("")
out.append("=== MANAGE_SCENE RESULT ===")
results = d.get("results", []) if isinstance(d, dict) else []
if not results and isinstance(d, dict) and "tool" in d:
    results = [d]
for i, r in enumerate(results):
    tool = r.get("tool", "?")
    out.append(f"Tool {i}: {tool}")
    if "error" in r:
        out.append("ERROR: " + str(r["error"]))
        continue
    result = r.get("result", r)
    if tool == "manage_scene":
        if isinstance(result, dict):
            h = result.get("hierarchy", result.get("data", result))
            if isinstance(h, list):
                out.append(f"Top-level GOs: {len(h)}")
                for go in h:
                    name = go.get("name", "?") if isinstance(go, dict) else str(go)
                    comps = go.get("components", []) if isinstance(go, dict) else []
                    cn = [c.get("type", "?") if isinstance(c, dict) else str(c) for c in comps] if isinstance(comps, list) else []
                    out.append(f"  {name}  comps={cn}")
            else:
                out.append(str(h)[:3000])
        else:
            out.append(str(result)[:3000])
    elif tool == "read_console":
        if isinstance(result, dict):
            logs = result.get("logs", result.get("entries", result.get("data", [])))
            if isinstance(logs, list):
                errs = [l for l in logs if isinstance(l, dict) and l.get("type", "").lower() in ("error", "exception")]
                warns = [l for l in logs if isinstance(l, dict) and l.get("type", "").lower() == "warning"]
                out.append(f"Total logs: {len(logs)}  Errors: {len(errs)}  Warnings: {len(warns)}")
                out.append("--- ERRORS ---")
                for l in errs:
                    out.append("  " + str(l.get("message", l.get("log", str(l)))[:300]))
                out.append("--- WARNINGS (first 15) ---")
                for l in warns[:15]:
                    out.append("  " + str(l.get("message", l.get("log", str(l)))[:200]))
            else:
                out.append(str(result)[:3000])
        else:
            out.append(str(result)[:3000])
    else:
        out.append(str(result)[:3000])
    out.append("")
with open("/content/mcp_summary.txt", "w") as f:
    f.write("\n".join(out))
print("SUMMARY_WRITTEN")
PYEOF
echo "=== SUMMARY ==="
cat /content/mcp_summary.txt