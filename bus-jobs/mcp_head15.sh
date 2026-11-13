#!/bin/bash
# mcp_head15.sh — test execute_code with simple code
python3 - <<'PYEOF'
import json
cmd = {
    "tool": "batch_execute",
    "params": {
        "commands": [
            {"tool": "execute_code", "params": {"code": "using UnityEngine; Debug.Log(\"EXECUTE_CODE_WORKS\"); return \"hello\";"}}
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
cd /content/work/mfps && /content/ue/Editor/Unity -batchmode -nographics -quit -projectPath /content/work/mfps -executeMethod McpBridge.Run -logFile /content/mcp_inspect6.log
echo "EDITOR_RC=$?"
test -f /content/mcp_result.json && echo "RESULT_EXISTS" || { echo NO_RESULT; tail -20 /content/mcp_inspect6.log; exit 6; }
echo "=== PARSE ==="
python3 - <<'PYEOF'
import json
d = json.load(open("/content/mcp_result.json"))
data = d.get("data", {})
for r in data.get("results", []):
    tool = r.get("tool", "?")
    res = r.get("result", {})
    print(f"--- {tool} ---")
    print(f"  success: {res.get('success') if isinstance(res, dict) else res}")
    print(f"  message: {res.get('message') if isinstance(res, dict) else ''}")
    rd = res.get("data", {}) if isinstance(res, dict) else {}
    print(f"  data: {str(rd)[:2000]}")
    print()
PYEOF