#!/bin/bash
# mcp_scene_inspect.sh — load HeistLevel, dump hierarchy + console via McpBridge
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR_BIN; exit 6; }
test -d "$PROJ/Assets/Editor" || { echo NO_PROJECT; exit 6; }
test -f "$PROJ/Assets/Editor/McpBridge.cs" || { echo NO_MCP_BRIDGE; exit 6; }
echo PREFLIGHT_OK

echo "=== WRITE COMMAND FILE ==="
python3 - <<'PYEOF'
import json
cmd = {
    "tool": "batch_execute",
    "params": {
        "commands": [
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
cd "$PROJ" && "$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod McpBridge.Run -logFile /content/mcp_inspect.log
echo "EDITOR_RC=$?"
test -f /content/mcp_result.json || { echo NO_RESULT_FILE; tail -30 /content/mcp_inspect.log; exit 6; }

echo "=== RESULT ==="
cat /content/mcp_result.json
echo ""
echo "MCP_INSPECT_DONE"
