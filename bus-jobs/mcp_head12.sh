#!/bin/bash
# mcp_head12.sh — load HeistLevel (action=load, path) + get hierarchy + console
python3 - <<'PYEOF'
import json
cmd = {
    "tool": "batch_execute",
    "params": {
        "commands": [
            {"tool": "manage_scene", "params": {"action": "load", "path": "MFPS/Scenes/HeistLevel.unity"}},
            {"tool": "manage_scene", "params": {"action": "get_hierarchy"}},
            {"tool": "read_console", "params": {}}
        ]
    }
}
with open("/content/mcp_command.json", "w") as f:
    json.dump(cmd, f)
print("COMMAND_WRITTEN")
PYEOF
echo "=== RUN MCP BRIDGE ==="
rm -f /content/mcp_result.json
mkdir -p /tmp/xdg; chmod 700 /tmp/xdg
export XDG_RUNTIME_DIR=/tmp/xdg
cd /content/work/mfps && /content/ue/Editor/Unity -batchmode -nographics -quit -projectPath /content/work/mfps -executeMethod McpBridge.Run -logFile /content/mcp_inspect5.log
echo "EDITOR_RC=$?"
test -f /content/mcp_result.json && echo "RESULT_EXISTS" || { echo NO_RESULT; tail -20 /content/mcp_inspect5.log; exit 6; }
echo "=== PARSE ==="
python3 - <<'PYEOF'
import json
d = json.load(open("/content/mcp_result.json"))
data = d.get("data", {})
for r in data.get("results", []):
    tool = r.get("tool", "?")
    res = r.get("result", {})
    print(f"--- {tool} ---")
    if isinstance(res, dict):
        print(f"  success: {res.get('success')}")
        print(f"  message: {res.get('message')}")
        rd = res.get("data", {})
        if tool == "manage_scene" and isinstance(rd, dict):
            items = rd.get("items", [])
            print(f"  total: {rd.get('total')}  items: {len(items)}")
            for go in items:
                name = go.get("name", "?") if isinstance(go, dict) else str(go)
                comps = go.get("components", []) if isinstance(go, dict) else []
                cn = [c.get("type", "?") if isinstance(c, dict) else str(c) for c in comps] if isinstance(comps, list) else []
                print(f"    {name}  comps={cn}")
        elif tool == "read_console" and isinstance(rd, list):
            errs = [l for l in rd if isinstance(l, dict) and l.get("type", "").lower() in ("error", "exception")]
            warns = [l for l in rd if isinstance(l, dict) and l.get("type", "").lower() == "warning"]
            logs = [l for l in rd if isinstance(l, dict) and l.get("type", "").lower() in ("log", "info")]
            print(f"  Total: {len(rd)}  Errors: {len(errs)}  Warnings: {len(warns)}  Logs: {len(logs)}")
            print("  --- ERRORS ---")
            for l in errs:
                print("    " + str(l.get("message", l.get("log", str(l)))[:300]))
            print("  --- LOGS (first 30) ---")
            for l in logs[:30]:
                print("    " + str(l.get("message", l.get("log", str(l)))[:200]))
            print("  --- WARNINGS (first 10) ---")
            for l in warns[:10]:
                print("    " + str(l.get("message", l.get("log", str(l)))[:200]))
        else:
            print(f"  data: {str(rd)[:1000]}")
    else:
        print(f"  result: {str(res)[:1000]}")
    print()
PYEOF