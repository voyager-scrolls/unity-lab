#!/usr/bin/env bash
set -u
# template_import_build_heist.sh
# MFPS 2.0 + POLYGON Heist Pack v1.5 -> new HeistLevel scene -> Windows build (offline mode, bots)
# Job result tail-truncates stdout at ~1500 chars -> print short markers, essentials LAST.

MFPSROOT=/content/drive/MyDrive/unity-lab/templates/mfps-2.0-v1.75
PKG=$MFPSROOT/mfps-2.0-v1.7.5.unitypackage
PUN2ZIP=$MFPSROOT/pun2-v2.16-mirror3.zip
HEISTPKG=$MFPSROOT/../assets/polygon-heist-v1.5/POLYGON-Heist-Pack-v1.5.unitypackage
ULF=/content/drive/MyDrive/unity-lab/secrets/Unity_lic.ulf
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
PEMB=/content/ue/Editor/Data/PlaybackEngines
STAMP=$(date +%s)

echo "=== PREFLIGHT ==="
test -f /content/unity_bin.txt || { echo NO_UNITY_BIN; exit 6; }
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -s "$PKG" || { echo NO_MFPS_PKG; exit 6; }
test -s "$PUN2ZIP" || { echo NO_PUN2_ZIP; exit 6; }
test -s "$HEISTPKG" || { echo NO_HEIST_PKG; exit 6; }
echo PREFLIGHT_OK

# --- licence (portable ULF, same recipe as cover-shooter job) ---
echo "=== LICENCE ==="
if [ -f "$ULF" ]; then
  mkdir -p /root/.local/share/unity3d/Unity
  cp "$ULF" /root/.local/share/unity3d/Unity/Unity_lic.ulf
  echo ULF_INSTALLED
else
  echo ULF_MISSING_WARN
fi

# --- ensure Windows standalone module (7z/pkg recipe) ---
echo "=== ENSURE WINDOWS MODULE ==="
if [ -d "$PEMB/WindowsStandaloneSupport" ] && [ -f "$PEMB/WindowsStandaloneSupport/UnityEditor.WindowsStandalone.Extensions.dll" ]; then
  echo WIN_MODULE_PRESENT
else
  TARB=/content/drive/MyDrive/unity-lab/cache/Windows.pkg
  if [ ! -s "$TARB" ]; then echo NO_WINDOWS_PKG_CACHE; exit 5; fi
  rm -rf /content/pkgm1 /content/pkgm2
  mkdir -p /content/pkgm1 /content/pkgm2
  7z x -y -o/content/pkgm1 "$TARB" >/dev/null 2>&1 || { echo PKG_EXTRACT_FAIL; exit 5; }
  cd /content/pkgm1
  # descend single-child chain until Payload* found
  while [ "$(ls -A . | wc -l)" = "1" ] && [ -d "$(ls -A .)" ]; do cd "$(ls -A .)"; done
  7z x -y -o/content/pkgm2 Payload* >/dev/null 2>&1 || { echo PAYLOAD_EXTRACT_FAIL; exit 5; }
  cd /content/pkgm2
  while [ "$(ls -A . | wc -l)" = "1" ] && [ -d "$(ls -A .)" ]; do cd "$(ls -A .)"; done
  cp -a . "$PEMB/WindowsStandaloneSupport" 2>/dev/null || { echo COPY_MODULE_FAIL; exit 5; }
  test -f "$PEMB/WindowsStandaloneSupport/UnityEditor.WindowsStandalone.Extensions.dll" && echo WIN_MODULE_EXTRACTED || { echo MODULE_DLL_MISSING; exit 5; }
fi

# --- create project if missing ---
echo "=== PROJECT ==="
if [ -d "$PROJ/Assets" ]; then
  echo PROJECT_EXISTS
else
  rm -rf "$PROJ"
  mkdir -p "$PROJ"
  "$UNITY" -batchmode -nographics -quit -createProject "$PROJ" -logFile /content/mfps_create.log >/dev/null 2>&1
  test -d "$PROJ/Assets" && echo PROJECT_CREATED || { echo PROJECT_CREATE_FAIL; tail -20 /content/mfps_create.log; exit 6; }
fi

# --- write Unity 6 manifest BEFORE any import (ugui + postprocessing + modules) ---
echo "=== WRITE UNITY6 MANIFEST (ugui + postprocessing + modules, BEFORE editor opens project) ==="
mkdir -p "$PROJ/Packages"
cat > "$PROJ/Packages/manifest.json" << 'MANIFESTEOF'
{
  "dependencies": {
    "com.unity.ugui": "2.0.0",
    "com.unity.postprocessing": "3.2.2",
    "com.unity.modules.ai": "1.0.0",
    "com.unity.modules.animation": "1.0.0",
    "com.unity.modules.audio": "1.0.0",
    "com.unity.modules.imgui": "1.0.0",
    "com.unity.modules.particlesystem": "1.0.0",
    "com.unity.modules.physics": "1.0.0",
    "com.unity.modules.terrain": "1.0.0",
    "com.unity.modules.ui": "1.0.0",
    "com.unity.modules.uielements": "1.0.0",
    "com.unity.modules.unitywebrequest": "1.0.0",
    "com.unity.modules.video": "1.0.0",
    "com.unity.modules.wind": "1.0.0"
  }
}
MANIFESTEOF
rm -f "$PROJ/Packages/packages-lock.json"
echo MANIFEST_WRITTEN

# --- install PUN2 (folder copy with metas, before MFPS import) ---
echo "=== INSTALL PUN2 ==="
rm -rf /content/pun2x
mkdir -p /content/pun2x
cd /content/pun2x
unzip -q -o "$PUN2ZIP" || { echo PUN2_UNZIP_FAIL; exit 6; }
cd /content
mkdir -p "$PROJ/Assets/Photon"
cp -a /content/pun2x/. "$PROJ/Assets/Photon/"
# remove the auto-installer so it can't hang in batchmode
rm -f "$PROJ/Assets/MFPS/Scripts/Internal/Editor/MFPS/ImportUPMDependencys.cs" "$PROJ/Assets/MFPS/Scripts/Internal/Editor/MFPS/ImportUPMDependencys.cs.meta" 2>/dev/null
test -f "$PROJ/Assets/Photon/PhotonUnityNetworking/Code/PhotonNetwork.cs" && echo PUN2_INSTALLED || { echo PUN2_INSTALL_FAIL; exit 6; }
PUN2CS=$(find "$PROJ/Assets/Photon" -name '*.cs' | wc -l)
echo "PUN2_CS=$PUN2CS"

# --- import MFPS core (tolerant) ---
echo "=== IMPORT MFPS CORE (tolerant) ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -importPackage "$PKG" -logFile /content/mfps_import.log >/dev/null 2>&1
echo "IMPORT_RC=$?"
test -d "$PROJ/Assets/MFPS" && echo MFPS_DIR_OK || { echo MFPS_DIR_MISSING; tail -20 /content/mfps_import.log; exit 6; }
MFPS_CS=$(find "$PROJ/Assets/MFPS" -name '*.cs' | wc -l)
echo "MFPS_CS=$MFPS_CS"

# --- rewrite manifest (import overwrites it) ---
echo "=== MANIFEST AGAIN ==="
cat > "$PROJ/Packages/manifest.json" << 'MANIFESTEOF'
{
  "dependencies": {
    "com.unity.ugui": "2.0.0",
    "com.unity.postprocessing": "3.2.2",
    "com.unity.modules.ai": "1.0.0",
    "com.unity.modules.animation": "1.0.0",
    "com.unity.modules.audio": "1.0.0",
    "com.unity.modules.imgui": "1.0.0",
    "com.unity.modules.particlesystem": "1.0.0",
    "com.unity.modules.physics": "1.0.0",
    "com.unity.modules.terrain": "1.0.0",
    "com.unity.modules.ui": "1.0.0",
    "com.unity.modules.uielements": "1.0.0",
    "com.unity.modules.unitywebrequest": "1.0.0",
    "com.unity.modules.video": "1.0.0",
    "com.unity.modules.wind": "1.0.0"
  }
}
MANIFESTEOF
rm -f "$PROJ/Packages/packages-lock.json"
echo MANIFEST_REWRITTEN

# --- import Heist pack (tolerant) ---
echo "=== IMPORT HEIST PACK (tolerant) ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -importPackage "$HEISTPKG" -logFile /content/heist_import.log >/dev/null 2>&1
echo "HEIST_IMPORT_RC=$?"
test -d "$PROJ/Assets/PolygonHeist" && echo HEIST_DIR_OK || { echo HEIST_DIR_MISSING; tail -20 /content/heist_import.log; exit 6; }

# --- perf script (low-end profile) ---
echo "=== PERF SCRIPT ==="
mkdir -p "$PROJ/Assets/Perf"
cp /content/drive/MyDrive/unity-lab/templates/mfps-2.0-v1.75/PerfTune.cs "$PROJ/Assets/Perf/PerfTune.cs" || { echo PERF_COPY_FAILED; exit 6; }
test -s "$PROJ/Assets/Perf/PerfTune.cs" && echo PERF_SCRIPT_WRITTEN || { echo PERF_SCRIPT_FAILED; exit 6; }

# --- scene builder (editor script) ---
echo "=== HEIST SCENE BUILDER ==="
mkdir -p "$PROJ/Assets/Editor"
cp /content/drive/MyDrive/unity-lab/templates/mfps-2.0-v1.75/HeistSceneBuilder.cs "$PROJ/Assets/Editor/HeistSceneBuilder.cs" || { echo BUILDER_COPY_FAILED; exit 6; }
test -s "$PROJ/Assets/Editor/HeistSceneBuilder.cs" && echo BUILDER_WRITTEN || { echo BUILDER_FAILED; exit 6; }

# --- offline mode (play ExampleLevel/HeistLevel directly, no Photon AppId) ---
echo "=== OFFLINE MODE (play HeistLevel directly, no Photon AppId) ==="
GD="$PROJ/Assets/MFPS/Resources/GameData.asset"
sed -i 's/  offlineMode: 0/  offlineMode: 1/' "$GD"
grep -n 'offlineMode: 1' "$GD" >/dev/null && echo OFFLINE_MODE_ON || { echo OFFLINE_FLIP_FAILED; grep -n 'offlineMode' "$GD"; exit 6; }

# --- compile gate ---
echo "=== COMPILE GATE ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -logFile /content/mfps_compile.log >/dev/null 2>&1
echo "COMPILE_RC=$?"
CSERR=$(grep -c 'error CS' /content/mfps_compile.log || true)
echo "CS_ERRORS=$CSERR"
if [ "$CSERR" != "0" ]; then
  echo "COMPILE_GATE_FAIL"
  grep -oE 'error CS[0-9]+: [^]]+' /content/mfps_compile.log | sort -u | head -25
  exit 6
fi
echo COMPILE_GATE_OK

# --- build HeistLevel scene via editor script ---
echo "=== BUILD HEIST SCENE ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod HeistSceneBuilder.Build -logFile /content/heist_scene.log >/dev/null 2>&1
echo "SCENE_BUILD_RC=$?"
grep -E 'HEIST_DONE|HEIST_LEVEL_SAVED|HEIST_LAYOUT_MISSING|error CS' /content/heist_scene.log | tail -10
grep -q 'HEIST_DONE' /content/heist_scene.log && echo HEIST_SCENE_OK || { echo HEIST_SCENE_FAILED; tail -20 /content/heist_scene.log; exit 6; }

# --- write build script (builds HeistLevel.unity) ---
echo "=== BUILD SCRIPT ==="
mkdir -p "$PROJ/Assets/Editor"
cat > "$PROJ/Assets/Editor/MfpsBuild.cs" << 'CSEOF'
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

public class MfpsBuild
{
    [MenuItem("MFPS/Build Windows")]
    public static void BuildWindows()
    {
        string scene = "Assets/MFPS/Scenes/HeistLevel.unity";
        if (!File.Exists(scene)) { Debug.LogError("SCENE_MISSING: " + scene); return; }
        string outDir = "Builds/Win";
        Directory.CreateDirectory(outDir);
        var opts = new BuildPlayerOptions();
        opts.scenes = new[] { scene };
        opts.locationPathName = outDir + "/MFPSPrototype.exe";
        opts.target = BuildTarget.StandaloneWindows64;
        opts.options = BuildOptions.None;
        var report = BuildPipeline.BuildPlayer(opts);
        Debug.Log("BUILD_RESULT " + report.summary.result + " errors=" + report.summary.totalErrors + " warnings=" + report.summary.totalWarnings + " size=" + report.summary.totalSize);
    }
}
CSEOF
echo BUILD_SCRIPT_WRITTEN

# --- build Windows ---
echo "=== BUILD WINDOWS ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod MfpsBuild.BuildWindows -logFile /content/mfps_build.log >/dev/null 2>&1
echo "BUILD_RC=$?"
grep -E 'BUILD_RESULT|error CS|Exception' /content/mfps_build.log | tail -5
grep -q 'BUILD_RESULT Succeeded' /content/mfps_build.log || { echo BUILD_FAILED; tail -15 /content/mfps_build.log; exit 6; }

# --- zip + stage ---
echo "=== STAGE ==="
cd "$PROJ/Builds/Win"
zip -r "/content/mfps-win-$STAMP.zip" . >/dev/null 2>&1
ls -lh "/content/mfps-win-$STAMP.zip"
rclone copyto "/content/mfps-win-$STAMP.zip" "gdrive:unity-lab/builds/mfps-win-$STAMP.zip" && echo MFPS_STAGED_OK || { echo STAGE_FAIL; exit 6; }
echo "MFPS_ZIP=mfps-win-$STAMP.zip"
echo "MFPS_BUNDLE_SIZE=$(du -sh /content/mfps-win-$STAMP.zip | cut -f1)"
