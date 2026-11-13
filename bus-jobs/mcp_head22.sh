#!/bin/bash
# mcp_head22.sh — search for GameManager prefab + inspect KillZone prefab components
python3 - <<'PYEOF'
import json
cmd = {
    "tool": "batch_execute",
    "params": {
        "commands": [
            {"tool": "manage_asset", "params": {"action": "search", "query": "GameManager", "type": "Prefab"}},
            {"tool": "manage_asset", "params": {"action": "search", "query": "KillZone", "type": "Prefab"}},
            {"tool": "manage_prefabs", "params": {"action": "get_info", "prefabPath": "Assets/MFPS/Prefabs/KillZone.prefab"}}
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
cd /content/work/mfps && /content/ue/Editor/Unity -batchmode -nographics -quit -projectPath /content/work/mfps -executeMethod McpBridge.Run -logFile /content/mcp_inspect7.log
echo "EDITOR_RC=$?"
test -f /content/mcp_result.json && echo "RESULT_EXISTS" || { echo NO_RESULT; tail -20 /content/mcp_inspect7.log; exit 6; }
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
        if isinstance(rd, list):
            print(f"  items: {len(rd)}")
            for item in rd[:20]:
                if isinstance(item, dict):
                    print(f"    {item.get('name','?')}  path={item.get('path','?')}  guid={item.get('guid','?')}")
                else:
                    print(f"    {str(item)[:300]}")
        elif isinstance(rd, dict):
            for k, v in rd.items():
                print(f"  {k}: {str(v)[:500]}")
        else:
            print(f"  data: {str(rd)[:2000]}")
    else:
        print(f"  result: {str(res)[:2000]}")
    print()
PYEOF