#!/bin/bash
# template_import_build_mcp.sh - MFPS project + MCPForUnity package + bridge test
# Tests: install package, compile, read_console, manage_scene get_hierarchy
set -e

UNITY=/content/ue/Editor/Unity
PEMB=/content/ue/Editor/Data/PlaybackEngines
PROJ=/content/work/mfps
MFPSROOT=/content/drive/MyDrive/unity-lab/templates/mfps-2.0-v1.75
PKG="$MFPSROOT/mfps-2.0-v1.7.5.unitypackage"
PUN2ZIP="$MFPSROOT/pun2-v2.16-mirror3.zip"
ULF=/content/drive/MyDrive/unity-lab/secrets/Unity_lic.ulf

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f /content/unity_bin.txt || { echo NO_UNITY_BIN; exit 6; }
test -s "$PKG" || { echo NO_MFPS_PKG; exit 6; }
test -s "$PUN2ZIP" || { echo NO_PUN2_ZIP; exit 6; }
echo PREFLIGHT_OK

echo "=== LICENCE ==="
if [ -f "$ULF" ]; then
  mkdir -p ~/.local/share/unity3d/Unity
  cp "$ULF" ~/.local/share/unity3d/Unity/Unity_lic.ulf
  echo ULF_INSTALLED
else
  echo ULF_MISSING_NONFATAL
fi

echo "=== ENSURE WINDOWS MODULE ==="
if [ -d "$PEMB/WindowsStandaloneSupport" ]; then
  echo WIN_MODULE_PRESENT
else
  TARB=/content/drive/MyDrive/unity-lab/cache/Windows.pkg
  if [ ! -s "$TARB" ]; then echo NO_WIN_CACHE; exit 5; fi
  rm -rf /tmp/pkgm1 /tmp/pkgm2
  mkdir -p /tmp/pkgm1 /tmp/pkgm2
  7z x "$TARB" -o/tmp/pkgm1 >/dev/null 2>&1 || { echo PKG_X_FAIL; exit 5; }
  PAYLOAD=$(find /tmp/pkgm1 -name 'Payload*' | head -1)
  7z x "$PAYLOAD" -o/tmp/pkgm2 >/dev/null 2>&1 || { echo PAYLOAD_X_FAIL; exit 5; }
  SRC=$(find /tmp/pkgm2 -name 'WindowsStandaloneSupport' -type d | head -1)
  cp -a "$SRC" "$PEMB/" || { echo CP_FAIL; exit 5; }
  echo WIN_MODULE_INSTALLED
fi

echo "=== CREATE OR REUSE PROJECT ==="
if [ -d "$PROJ/Assets" ]; then
  echo PROJECT_EXISTS
else
  mkdir -p /content/work
  "$UNITY" -batchmode -nographics -quit -createProject "$PROJ" -logFile /content/mfps_create.log
  echo "CREATE_RC=$?"
  test -d "$PROJ/Assets" || { echo CREATE_FAILED; tail -20 /content/mfps_create.log; exit 6; }
  echo PROJECT_CREATED
fi

echo "=== WRITE UNITY6 MANIFEST (ugui + postprocessing + mcp + modules, BEFORE editor opens project) ==="
python3 - "$PROJ" <<'PYEOF'
import json, sys, os
proj = sys.argv[1]
manifest = {
  "dependencies": {
    "com.unity.ugui": "2.0.0",
    "com.unity.postprocessing": "3.2.2",
    "com.unity.nuget.newtonsoft-json": "3.2.0",
    "com.coplaydev.unity-mcp": "https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main",
    "com.unity.modules.ai": "1.0.0",
    "com.unity.modules.animation": "1.0.0",
    "com.unity.modules.audio": "1.0.0",
    "com.unity.modules.imgui": "1.0.0",
    "com.unity.modules.particlesystem": "1.0.0",
    "com.unity.modules.physics": "1.0.0",
    "com.unity.modules.physics2d": "1.0.0",
    "com.unity.modules.terrain": "1.0.0",
    "com.unity.modules.terrainphysics": "1.0.0",
    "com.unity.modules.ui": "1.0.0",
    "com.unity.modules.uielements": "1.0.0",
    "com.unity.modules.unitywebrequest": "1.0.0",
    "com.unity.modules.video": "1.0.0"
  }
}
os.makedirs(os.path.join(proj, "Packages"), exist_ok=True)
with open(os.path.join(proj, "Packages", "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2)
print("MANIFEST_WRITTEN")
PYEOF

echo "=== INSTALL PUN2 (folder copy with metas, before any MFPS import) ==="
if [ -f "$PROJ/Assets/Photon/PhotonUnityNetworking/Code/PhotonNetwork.cs" ]; then
  echo PUN2_ALREADY_INSTALLED
else
  rm -rf /content/pun2x
  mkdir -p /content/pun2x
  unzip -q "$PUN2ZIP" -d /content/pun2x || { echo PUN2_UNZIP_FAIL; exit 6; }
  mkdir -p "$PROJ/Assets/Photon"
  cp -a /content/pun2x/. "$PROJ/Assets/Photon/" || { echo PUN2_CP_FAIL; exit 6; }
  # Fix PrefabStageUtility namespace for Unity 6
  sed -i 's/UnityEditor\.Experimental\.SceneManagement\.PrefabStageUtility/UnityEditor.SceneManagement.PrefabStageUtility/g' "$PROJ/Assets/Photon/PhotonUnityNetworking/Code/Editor/PhotonEditorUtils.cs" 2>/dev/null || true
  echo "PUN2_INSTALLED"
fi
PUN2_CS=$(find "$PROJ/Assets/Photon" -name '*.cs' | wc -l)
echo "PUN2_CS=$PUN2_CS"

echo "=== IMPORT MFPS CORE (tolerant) ==="
if [ -d "$PROJ/Assets/MFPS" ]; then
  echo MFPS_ALREADY_IMPORTED
else
  "$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -importPackage "$PKG" -logFile /content/mfps_import.log
  echo "IMPORT_RC=$?"
fi
MFPS_CS=$(find "$PROJ/Assets/MFPS" -name '*.cs' 2>/dev/null | wc -l)
echo "MFPS_CS=$MFPS_CS"
test -d "$PROJ/Assets/MFPS" || { echo MFPS_DIR_MISSING; exit 6; }

echo "=== REMOVE IMPORTUPMDEPENDENCYS (postprocessing pre-installed) ==="
rm -f "$PROJ/Assets/MFPS/Scripts/Internal/Editor/MFPS/ImportUPMDependencys.cs" "$PROJ/Assets/MFPS/Scripts/Internal/Editor/MFPS/ImportUPMDependencys.cs.meta" 2>/dev/null
echo "IMPORTER_REMOVED"

echo "=== MANIFEST AGAIN (package import may have overwritten) ==="
python3 - "$PROJ" <<'PYEOF'
import json, sys, os
proj = sys.argv[1]
manifest = {
  "dependencies": {
    "com.unity.ugui": "2.0.0",
    "com.unity.postprocessing": "3.2.2",
    "com.unity.nuget.newtonsoft-json": "3.2.0",
    "com.coplaydev.unity-mcp": "https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main",
    "com.unity.modules.ai": "1.0.0",
    "com.unity.modules.animation": "1.0.0",
    "com.unity.modules.audio": "1.0.0",
    "com.unity.modules.imgui": "1.0.0",
    "com.unity.modules.particlesystem": "1.0.0",
    "com.unity.modules.physics": "1.0.0",
    "com.unity.modules.physics2d": "1.0.0",
    "com.unity.modules.terrain": "1.0.0",
    "com.unity.modules.terrainphysics": "1.0.0",
    "com.unity.modules.ui": "1.0.0",
    "com.unity.modules.uielements": "1.0.0",
    "com.unity.modules.unitywebrequest": "1.0.0",
    "com.unity.modules.video": "1.0.0"
  }
}
with open(os.path.join(proj, "Packages", "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2)
print("MANIFEST_REWRITTEN")
PYEOF
rm -f "$PROJ/Packages/packages-lock.json" 2>/dev/null
echo "LOCK_REMOVED"

echo "=== WRITE MCP BRIDGE ==="
mkdir -p "$PROJ/Assets/Editor"
cat > "$PROJ/Assets/Editor/McpBridge.cs" << 'CSEOF'
using System;
using System.IO;
using System.Threading.Tasks;
using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Tools;
using MCPForUnity.Editor.Tools.GameObjects;
using MCPForUnity.Editor.Tools.Prefabs;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;

public static class McpBridge
{
    private const string CommandFile = "/content/mcp_command.json";
    private const string ResultFile = "/content/mcp_result.json";

    public static void Run()
    {
        try
        {
            if (!File.Exists(CommandFile))
            {
                WriteResult("{\"success\":false,\"error\":\"No command file at " + CommandFile + "\"}");
                return;
            }

            string json = File.ReadAllText(CommandFile);
            var cmd = JObject.Parse(json);
            string tool = cmd["tool"]?.ToString();
            var p = cmd["params"] as JObject ?? new JObject();

            object result = null;
            switch (tool)
            {
                case "read_console":
                    result = ReadConsole.HandleCommand(p);
                    break;
                case "manage_scene":
                    result = ManageScene.HandleCommand(p);
                    break;
                case "manage_asset":
                    result = ManageAsset.HandleCommand(p);
                    break;
                case "manage_prefabs":
                    result = ManagePrefabs.HandleCommand(p);
                    break;
                case "execute_code":
                    result = ExecuteCode.HandleCommand(p);
                    break;
                case "batch_execute":
                    var task = BatchExecute.HandleCommand(p);
                    task.GetAwaiter().GetResult();
                    result = task.Result;
                    break;
                case "manage_gameobject":
                    result = ManageGameObject.HandleCommand(p);
                    break;
                default:
                    result = new ErrorResponse("Unknown tool: " + tool);
                    break;
            }

            string resultJson = JsonConvert.SerializeObject(result);
            WriteResult(resultJson);
            Debug.Log("MCP_BRIDGE_RESULT: " + resultJson);
        }
        catch (Exception e)
        {
            string errJson = JsonConvert.SerializeObject(new { success = false, error = e.ToString() });
            WriteResult(errJson);
            Debug.LogError("MCP_BRIDGE_ERROR: " + e);
        }
    }

    private static void WriteResult(string json)
    {
        File.WriteAllText(ResultFile, json);
    }
}
CSEOF
echo "BRIDGE_WRITTEN"

echo "=== COMPILE GATE ==="
rm -rf "$PROJ/Temp"
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod McpBridge.Run -logFile /content/mcp_compile.log
COMPILE_RC=$?
echo "COMPILE_RC=$COMPILE_RC"
CS_ERRORS=$(grep -c "error CS" /content/mcp_compile.log 2>/dev/null || echo 0)
echo "CS_ERRORS=$CS_ERRORS"
if [ "$CS_ERRORS" != "0" ]; then
  echo "COMPILE_GATE_FAIL"
  grep -n "error CS" /content/mcp_compile.log | head -25
  exit 6
fi
echo "COMPILE_GATE_OK"

echo "=== TEST 1: read_console ==="
echo '{"tool":"read_console","params":{"action":"get","types":["error","warning","log"],"count":20}}' > /content/mcp_command.json
rm -f /content/mcp_result.json
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod McpBridge.Run -logFile /content/mcp_test1.log
echo "TEST1_RC=$?"
if [ -f /content/mcp_result.json ]; then
  echo "TEST1_RESULT:"
  cat /content/mcp_result.json
  echo ""
else
  echo "TEST1_NO_RESULT"
  grep -i "MCP_BRIDGE" /content/mcp_test1.log | tail -5
fi

echo "=== TEST 2: manage_scene get_hierarchy ==="
echo '{"tool":"manage_scene","params":{"action":"get_hierarchy","pageSize":20}}' > /content/mcp_command.json
rm -f /content/mcp_result.json
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod McpBridge.Run -logFile /content/mcp_test2.log
echo "TEST2_RC=$?"
if [ -f /content/mcp_result.json ]; then
  echo "TEST2_RESULT:"
  cat /content/mcp_result.json
  echo ""
else
  echo "TEST2_NO_RESULT"
  grep -i "MCP_BRIDGE" /content/mcp_test2.log | tail -5
fi

echo "MCP_SETUP_DONE"
