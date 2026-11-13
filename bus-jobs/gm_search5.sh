#!/bin/bash
# gm_search5.sh — get raw prefab hierarchy JSON
python3 - <<'PYEOF'
import json
cmd = {
    "tool": "batch_execute",
    "params": {
        "commands": [
            {"tool": "manage_prefabs", "params": {"action": "get_hierarchy", "prefabPath": "Assets/MFPS/Content/Prefabs/Network/GameManager.prefab"}},
            {"tool": "manage_prefabs", "params": {"action": "get_hierarchy", "prefabPath": "Assets/MFPS/Content/Prefabs/GamePlay/Level/KillZone.prefab"}}
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
cd /content/work/mfps && /content/ue/Editor/Unity -batchmode -nographics -quit -projectPath /content/work/mfps -executeMethod McpBridge.Run -logFile /content/mcp_gm5.log
echo "EDITOR_RC=$?"
test -f /content/mcp_result.json && echo "RESULT_EXISTS" || { echo NO_RESULT; tail -20 /content/mcp_gm5.log; exit 6; }
python3 - <<'PYEOF'
import json
d = json.load(open("/content/mcp_result.json"))
data = d.get("data", {})
for r in data.get("results", []):
    tool = r.get("tool", "?")
    res = r.get("result", {})
    print(f"--- {tool} ---")
    rd = res.get("data", {}) if isinstance(res, dict) else {}
    # Print raw data structure
    print(json.dumps(rd, indent=2)[:3000])
    print()
PYEOF