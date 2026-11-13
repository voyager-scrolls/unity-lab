#!/bin/bash
# gm_search4.sh — inspect GameManager + KillZone prefab hierarchies
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
cd /content/work/mfps && /content/ue/Editor/Unity -batchmode -nographics -quit -projectPath /content/work/mfps -executeMethod McpBridge.Run -logFile /content/mcp_gm4.log
echo "EDITOR_RC=$?"
test -f /content/mcp_result.json && echo "RESULT_EXISTS" || { echo NO_RESULT; tail -20 /content/mcp_gm4.log; exit 6; }
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
        if isinstance(rd, dict):
            # Try to print hierarchy
            def print_tree(node, indent=0):
                if isinstance(node, dict):
                    name = node.get("name", "?")
                    comps = node.get("components", [])
                    cn = []
                    for c in comps:
                        if isinstance(c, dict):
                            cn.append(c.get("type", c.get("name", "?")))
                        else:
                            cn.append(str(c))
                    print("  " * indent + f"{name}  comps={cn}")
                    children = node.get("children", node.get("childGameObjects", []))
                    if isinstance(children, list):
                        for child in children:
                            print_tree(child, indent + 1)
                elif isinstance(node, list):
                    for item in node:
                        print_tree(item, indent)
            # Try different keys for hierarchy
            for key in ["hierarchy", "root", "gameObject", "items", "children"]:
                if key in rd:
                    print(f"  (key: {key})")
                    print_tree(rd[key])
                    break
            else:
                print(f"  keys: {list(rd.keys())}")
                print(f"  data: {str(rd)[:2000]}")
        elif isinstance(rd, list):
            print(f"  items: {len(rd)}")
            for item in rd[:20]:
                print(f"    {str(item)[:300]}")
        else:
            print(f"  data: {str(rd)[:2000]}")
    else:
        print(f"  result: {str(res)[:2000]}")
    print()
PYEOF