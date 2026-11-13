#!/bin/bash
# template_import_build_mfps.sh - import MFPS 2.0 core + PUN2 (mirror) into Unity 6, build ExampleLevel offline.
# Ordering rules learned from the cover-shooter gate:
#   (1) Unity-6 manifest must be correct BEFORE the editor opens the project.
#   (2) PUN2 folder must be in Assets BEFORE the MFPS import pass so everything compiles together.
#   (3) MFPS's own ImportUPMDependencys.cs self-deletes when com.unity.postprocessing is already
#       resolved - package resolution happens before InitializeOnLoad, so manifest-first is enough.
# Offline mode: GameData.asset offlineMode 0->1 lets ExampleLevel play directly, no Photon AppId.
set -u

UNITY=/content/ue/Editor/Unity
PEMB=/content/ue/Editor/Data/PlaybackEngines
PROJ=/content/work/mfps
MFPSROOT=/content/drive/MyDrive/unity-lab/templates/mfps-2.0-v1.75
PKG=$MFPSROOT/mfps-2.0-v1.7.5.unitypackage
PUN2ZIP=$MFPSROOT/pun2-v2.16-mirror3.zip
STAMP=$(date +%s)
OUT=/content/mfps-win.zip
DRIVE_OUT=/content/drive/MyDrive/unity-lab/builds
WPKG=/content/drive/MyDrive/unity-lab/cache/Windows.pkg
WURL="https://download.unity3d.com/download_unity/e35f0c77bd8e/MacEditorTargetInstaller/UnitySetup-Windows-Mono-Support-for-Editor-6000.3.10f1.pkg"

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR_BIN; exit 6; }
test -s "$PKG" || { echo NO_MFPS_PACKAGE; exit 6; }
test -s "$PUN2ZIP" || { echo NO_PUN2_ZIP; exit 6; }
test -s /content/drive/MyDrive/unity-lab/secrets/Unity_lic.ulf || echo NO_ULF_WARN
echo PREFLIGHT_OK

echo "=== LICENCE ==="
mkdir -p "$HOME/.local/share/unity3d/Unity"
if [ -f /content/drive/MyDrive/unity-lab/secrets/Unity_lic.ulf ]; then
  cp /content/drive/MyDrive/unity-lab/secrets/Unity_lic.ulf "$HOME/.local/share/unity3d/Unity/Unity_lic.ulf"
  chmod 600 "$HOME/.local/share/unity3d/Unity/Unity_lic.ulf"
  echo ULF_INSTALLED
fi

echo "=== ENSURE WINDOWS MODULE ==="
if [ -f "$PEMB/WindowsStandaloneSupport/UnityEditor.WindowsStandalone.Extensions.dll" ]; then
  echo WIN_MODULE_PRESENT
else
  if [ ! -s "$WPKG" ]; then
    aria2c --allow-overwrite=true -x8 -d /content -o Windows.pkg "$WURL" || { echo WIN_DL_FAIL; exit 5; }
    cp /content/Windows.pkg "$WPKG" 2>/dev/null || true
    WPKG=/content/Windows.pkg
  fi
  rm -rf /content/pkgm1 /content/pkgm2; mkdir -p /content/pkgm1 /content/pkgm2
  7z x -y "$WPKG" -o/content/pkgm1 >/dev/null || { echo WIN_7Z_FAIL; exit 5; }
  PAY=$(ls /content/pkgm1 | grep -i '^payload' | head -1)
  [ -n "$PAY" ] || { echo WIN_NO_PAYLOAD; exit 5; }
  7z x -y "/content/pkgm1/$PAY" -o/content/pkgm2 >/dev/null || { echo WIN_PAYLOAD_7Z_FAIL; exit 5; }
  SRC=/content/pkgm2
  while true; do
    N=$(ls "$SRC" | wc -l); E=$(ls "$SRC" | head -1)
    if [ "$N" = 1 ] && [ -d "$SRC/$E" ] && [ "$E" != "WindowsStandaloneSupport" ]; then SRC="$SRC/$E"; else break; fi
  done
  mkdir -p "$PEMB/WindowsStandaloneSupport"
  cp -a "$SRC/." "$PEMB/WindowsStandaloneSupport/"
  [ -f "$PEMB/WindowsStandaloneSupport/UnityEditor.WindowsStandalone.Extensions.dll" ] && echo WIN_MODULE_INSTALLED || { echo WIN_LAYOUT_BAD; exit 5; }
fi

if [ ! -d "$PROJ/Assets" ]; then
  "$UNITY" -batchmode -nographics -quit -createProject "$PROJ" -logFile /content/mfps_create.log || { echo CREATE_FAILED; exit 6; }
  echo CREATE_PROJECT_OK
else
  echo PROJECT_EXISTS
fi

echo "=== WRITE UNITY6 MANIFEST (ugui + postprocessing + modules, BEFORE editor opens project) ==="
mkdir -p "$PROJ/Packages"
python3 - "$PROJ/Packages/manifest.json" <<'PYEOF'
import json, sys
deps = {
    "com.unity.ugui": "2.0.0",
    "com.unity.postprocessing": "3.2.2",
    "com.unity.modules.ai": "1.0.0",
    "com.unity.modules.animation": "1.0.0",
    "com.unity.modules.audio": "1.0.0",
    "com.unity.modules.imageconversion": "1.0.0",
    "com.unity.modules.imgui": "1.0.0",
    "com.unity.modules.jsonserialize": "1.0.0",
    "com.unity.modules.particlesystem": "1.0.0",
    "com.unity.modules.physics": "1.0.0",
    "com.unity.modules.physics2d": "1.0.0",
    "com.unity.modules.screencapture": "1.0.0",
    "com.unity.modules.terrain": "1.0.0",
    "com.unity.modules.terrainphysics": "1.0.0",
    "com.unity.modules.ui": "1.0.0",
    "com.unity.modules.uielements": "1.0.0",
    "com.unity.modules.unitywebrequest": "1.0.0",
    "com.unity.modules.video": "1.0.0",
    "com.unity.modules.wind": "1.0.0"
}
open(sys.argv[1], "w").write(json.dumps({"dependencies": deps}, indent=2))
print("MANIFEST_WRITTEN")
PYEOF
rm -f "$PROJ/Packages/packages-lock.json"

echo "=== INSTALL PUN2 (folder copy with metas, before any MFPS import) ==="
rm -rf /content/pun2x; mkdir -p /content/pun2x
unzip -q "$PUN2ZIP" -d /content/pun2x || { echo PUN2_UNZIP_FAIL; exit 5; }
rm -rf "$PROJ/Assets/Photon"
cp -a /content/pun2x "$PROJ/Assets/Photon"
test -f "$PROJ/Assets/Photon/PhotonUnityNetworking/Code/PhotonNetwork.cs" && echo PUN2_INSTALLED || { echo PUN2_FILES_MISSING; exit 5; }
echo "PUN2_CS=$(find "$PROJ/Assets/Photon" -name '*.cs' | wc -l)"

echo "=== IMPORT MFPS CORE (tolerant) ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -importPackage "$PKG" -logFile /content/mfps_import.log
echo "IMPORT_RC=$?"
test -d "$PROJ/Assets/MFPS" && echo MFPS_DIR_OK || { echo MFPS_DIR_MISSING; exit 6; }
echo "MFPS_CS=$(find "$PROJ/Assets/MFPS" -name '*.cs' | wc -l)"
# the postprocessing auto-installer should have deleted itself; if not, kill it to protect the compile gate
rm -f "$PROJ/Assets/MFPS/Scripts/Internal/Editor/MFPS/ImportUPMDependencys.cs" "$PROJ/Assets/MFPS/Scripts/Internal/Editor/MFPS/ImportUPMDependencys.cs.meta" 2>/dev/null && echo IMPORTER_REMOVED

echo "=== MANIFEST AGAIN ==="
python3 - "$PROJ/Packages/manifest.json" <<'PYEOF'
import json, sys
deps = {
    "com.unity.ugui": "2.0.0",
    "com.unity.postprocessing": "3.2.2",
    "com.unity.modules.ai": "1.0.0",
    "com.unity.modules.animation": "1.0.0",
    "com.unity.modules.audio": "1.0.0",
    "com.unity.modules.imageconversion": "1.0.0",
    "com.unity.modules.imgui": "1.0.0",
    "com.unity.modules.jsonserialize": "1.0.0",
    "com.unity.modules.particlesystem": "1.0.0",
    "com.unity.modules.physics": "1.0.0",
    "com.unity.modules.physics2d": "1.0.0",
    "com.unity.modules.screencapture": "1.0.0",
    "com.unity.modules.terrain": "1.0.0",
    "com.unity.modules.terrainphysics": "1.0.0",
    "com.unity.modules.ui": "1.0.0",
    "com.unity.modules.uielements": "1.0.0",
    "com.unity.modules.unitywebrequest": "1.0.0",
    "com.unity.modules.video": "1.0.0",
    "com.unity.modules.wind": "1.0.0"
}
open(sys.argv[1], "w").write(json.dumps({"dependencies": deps}, indent=2))
print("MANIFEST_REWRITTEN")
PYEOF
rm -f "$PROJ/Packages/packages-lock.json"

echo "=== PERF SCRIPT (low-end profile: no post-processing, cheap shadows, 720p window, FPS readout) ==="
mkdir -p "$PROJ/Assets/Perf"
cp /content/drive/MyDrive/unity-lab/templates/mfps-2.0-v1.75/PerfTune.cs "$PROJ/Assets/Perf/PerfTune.cs" || { echo PERF_COPY_FAILED; exit 6; }
test -s "$PROJ/Assets/Perf/PerfTune.cs" && echo PERF_SCRIPT_WRITTEN || { echo PERF_SCRIPT_FAILED; exit 6; }

echo "=== HEIST SCENE BUILDER ==="
mkdir -p "$PROJ/Assets/Editor"
cp /content/drive/MyDrive/unity-lab/templates/mfps-2.0-v1.75/HeistSceneBuilder.cs "$PROJ/Assets/Editor/HeistSceneBuilder.cs" || { echo HEIST_BUILDER_COPY_FAILED; exit 6; }
test -s "$PROJ/Assets/Editor/HeistSceneBuilder.cs" && echo HEIST_BUILDER_WRITTEN || { echo HEIST_BUILDER_FAILED; exit 6; }

echo "=== REMOVE MCP BRIDGE (dev tool, not part of game build) ==="
rm -f "$PROJ/Assets/Editor/McpBridge.cs" "$PROJ/Assets/Editor/McpBridge.cs.meta"
echo "MCP_BRIDGE_REMOVED"

echo "=== COMPILE GATE ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -logFile /content/mfps_compile.log
echo "COMPILE_RC=$?"
ERRS=$(grep -cE "error CS" /content/mfps_compile.log)
echo "CS_ERRORS=$ERRS"
if [ "$ERRS" != 0 ]; then
  echo COMPILE_GATE_FAILED
  grep -E "error CS" /content/mfps_compile.log | sed -E 's/^.*Assets/Assets/' | sort -u | head -25
  exit 6
fi
echo COMPILE_GATE_OK

echo "=== OFFLINE MODE (play ExampleLevel directly, no Photon AppId) ==="
GD="$PROJ/Assets/MFPS/Resources/GameData.asset"
test -s "$GD" || { echo GAMEDATA_MISSING; exit 6; }
sed -i 's/  offlineMode: 0/  offlineMode: 1/' "$GD"
grep -n 'offlineMode: 1' "$GD" || { echo OFFLINE_FLIP_FAILED; exit 6; }
echo OFFLINE_MODE_ON

echo "=== BUILD SCRIPT ==="
mkdir -p "$PROJ/Assets/Editor"
cat > "$PROJ/Assets/Editor/MfpsBuild.cs" << 'CSEOF'
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

public class MfpsBuild {
    public static void Perform() {
        string scene = "Assets/MFPS/Scenes/HeistLevel.unity";
        if (!File.Exists(scene)) {
            Debug.LogError("MISSING_SCENE " + scene);
            EditorApplication.Exit(6);
        }
        PlayerSettings.companyName = "VoyagerScrolls";
        PlayerSettings.productName = "MFPSPrototype";
        Directory.CreateDirectory("Builds/Win");
        var opts = new BuildPlayerOptions {
            scenes = new string[] { scene },
            locationPathName = "Builds/Win/MFPSPrototype.exe",
            target = BuildTarget.StandaloneWindows64,
            targetGroup = BuildTargetGroup.Standalone,
            options = BuildOptions.None
        };
        var rep = BuildPipeline.BuildPlayer(opts);
        var sum = rep.summary;
        Debug.Log("BUILD_RESULT " + sum.result + " errors=" + sum.totalErrors + " warnings=" + sum.totalWarnings + " size=" + sum.totalSize);
        if (sum.result != BuildResult.Succeeded) {
            EditorApplication.Exit(1);
        }
    }
}
CSEOF

echo "=== BUILD HEIST SCENE ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod CoverShooter.HeistSceneBuilder.BuildHeistScene -logFile /content/mfps_heist_scene.log
echo "HEIST_SCENE_RC=$?"
grep -nE "INSTANTIATED|CREATED|NAV MESH|HEIST_SCENE_SAVED|BUILD_SCENES_SET|ERROR|Exception" /content/mfps_heist_scene.log | head -25
if grep -q "HEIST_SCENE_SAVED" /content/mfps_heist_scene.log; then
  echo HEIST_SCENE_OK
else
  echo HEIST_SCENE_FAILED
  tail -20 /content/mfps_heist_scene.log
  exit 6
fi

echo "=== BUILD WINDOWS ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod MfpsBuild.Perform -logFile /content/mfps_build.log
BRC=$?
echo "BUILD_RC=$BRC"
grep -nE "BUILD_RESULT|MISSING_SCENE" /content/mfps_build.log | head -5
if [ "$BRC" != 0 ]; then
  echo MFPS_BUILD_FAILED
  grep -E "error CS|Exception|Error building" /content/mfps_build.log | head -15
  exit 6
fi
test -f "$PROJ/Builds/Win/MFPSPrototype.exe" || { echo NO_EXE; ls -la "$PROJ/Builds/Win" 2>&1; exit 6; }

echo "=== STAGE ==="
rm -f "$OUT"
cd "$PROJ/Builds/Win" && zip -qr "$OUT" .
mkdir -p "$DRIVE_OUT"
cp "$OUT" "$DRIVE_OUT/mfps-win-$STAMP.zip"
echo "MFPS_BUNDLE_SIZE=$(du -sh "$OUT" | cut -f1)"
echo "MFPS_ZIP=mfps-win-$STAMP.zip"
echo MFPS_STAGED_OK
