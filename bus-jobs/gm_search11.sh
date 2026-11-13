#!/bin/bash
# gm_search11.sh — get full ExampleLevel hierarchy with components (maxDepth)
python3 - <<'PYEOF'
import json
cmd = {
    "tool": "batch_execute",
    "params": {
        "commands": [
            {"tool": "manage_scene", "params": {"action": "load", "path": "MFPS/Scenes/ExampleLevel.unity"}},
            {"tool": "manage_scene", "params": {"action": "get_hierarchy", "maxDepth": 5, "pageSize": 200}}
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
cd /content/work/mfps && /content/ue/Editor/Unity -batchmode -nographics -quit -projectPath /content/work/mfps -executeMethod McpBridge.Run -logFile /content/mcp_gm11.log
echo "EDITOR_RC=$?"
test -f /content/mcp_result.json && echo "RESULT_EXISTS" || { echo NO_RESULT; tail -20 /content/mcp_gm11.log; exit 6; }
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
            items = rd.get("items", [])
            print(f"  total: {rd.get('total')}  items: {len(items)}")
            for go in items:
                if isinstance(go, dict):
                    name = go.get("name", "?")
                    comps = go.get("componentTypes", go.get("components", []))
                    cn = comps if isinstance(comps, list) else []
                    print(f"    {name}  comps={cn}")
                    children = go.get("children", [])
                    if isinstance(children, list):
                        for child in children:
                            if isinstance(child, dict):
                                cname = child.get("name", "?")
                                ccomps = child.get("componentTypes", child.get("components", []))
                                ccn = ccomps if isinstance(ccomps, list) else []
                                print(f"      {cname}  comps={ccn}")
        elif isinstance(rd, list):
            print(f"  items: {len(rd)}")
            for item in rd[:50]:
                if isinstance(item, dict):
                    print(f"    {item.get('name','?')}  comps={item.get('componentTypes', item.get('components', []))}")
                else:
                    print(f"    {str(item)[:300]}")
        else:
            print(f"  data: {str(rd)[:3000]}")
    else:
        print(f"  result: {str(res)[:3000]}")
    print()
PYEOF