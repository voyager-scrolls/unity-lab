#!/bin/bash
# gm_search6.sh — get full GameManager prefab component list (first result only)
python3 - <<'PYEOF'
import json
cmd = {
    "tool": "batch_execute",
    "params": {
        "commands": [
            {"tool": "manage_prefabs", "params": {"action": "get_hierarchy", "prefabPath": "Assets/MFPS/Content/Prefabs/Network/GameManager.prefab"}}
        ]
    }
}
with open("/content/mcp_command.json", "w") as f:
    json.dump(cmd, f)
print("COMMAND_WRITTEN")
PYEOF
rm -f /content/mcp_result.json
mkdir -p /tmp/xdg; chmod 700 /tmp/xdg
export XDG_RUNTIME_DIR=/tmp/xdg
cd /content/work/mfps && /content/ue/Editor/Unity -batchmode -nographics -quit -projectPath /content/work/mfps -executeMethod McpBridge.Run -logFile /content/mcp_gm6.log
echo "EDITOR_RC=$?"
test -f /content/mcp_result.json && echo "RESULT_EXISTS" || { echo NO_RESULT; tail -20 /content/mcp_gm6.log; exit 6; }
python3 - <<'PYEOF'
import json
d = json.load(open("/content/mcp_result.json"))
data = d.get("data", {})
for r in data.get("results", []):
    res = r.get("result", {})
    rd = res.get("data", {}) if isinstance(res, dict) else {}
    items = rd.get("items", [])
    for item in items:
        if isinstance(item, dict):
            name = item.get("name", "?")
            comps = item.get("componentTypes", [])
            print(f"{name}: {comps}")
PYEOF