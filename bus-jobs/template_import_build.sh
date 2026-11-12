#!/bin/bash
# template_import_build.sh v2 - import Asset Store package into Unity 6 and build Windows.
# v2 fixes the ordering bug: the manifest must be Unity-6-correct BEFORE the editor opens
# the project (v1 restored it after import, so the import pass compiled without ugui).
set -u

UNITY=/content/ue/Editor/Unity
PEMB=/content/ue/Editor/Data/PlaybackEngines
PROJ=/content/work/tmpl
PKG=/content/drive/MyDrive/unity-lab/templates/covershooter-1.6.2.unitypackage
STAMP=$(date +%s)
OUT=/content/tmpl-win.zip
DRIVE_OUT=/content/drive/MyDrive/unity-lab/builds
WPKG=/content/drive/MyDrive/unity-lab/cache/Windows.pkg
WURL="https://download.unity3d.com/download_unity/e35f0c77bd8e/MacEditorTargetInstaller/UnitySetup-Windows-Mono-Support-for-Editor-6000.3.10f1.pkg"

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR_BIN; exit 6; }
test -s "$PKG" || { echo NO_PACKAGE; exit 6; }
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
  rm -rf /content/pkgx1 /content/pkgx2; mkdir -p /content/pkgx1 /content/pkgx2
  7z x -y "$WPKG" -o/content/pkgx1 >/dev/null || { echo WIN_7Z_FAIL; exit 5; }
  PAY=$(ls /content/pkgx1 | grep -i '^payload' | head -1)
  [ -n "$PAY" ] || { echo WIN_NO_PAYLOAD; exit 5; }
  7z x -y "/content/pkgx1/$PAY" -o/content/pkgx2 >/dev/null || { echo WIN_PAYLOAD_7Z_FAIL; exit 5; }
  SRC=/content/pkgx2
  while true; do
    N=$(ls "$SRC" | wc -l); E=$(ls "$SRC" | head -1)
    if [ "$N" = 1 ] && [ -d "$SRC/$E" ] && [ "$E" != "WindowsStandaloneSupport" ]; then SRC="$SRC/$E"; else break; fi
  done
  mkdir -p "$PEMB/WindowsStandaloneSupport"
  cp -a "$SRC/." "$PEMB/WindowsStandaloneSupport/"
  [ -f "$PEMB/WindowsStandaloneSupport/UnityEditor.WindowsStandalone.Extensions.dll" ] && echo WIN_MODULE_INSTALLED || { echo WIN_LAYOUT_BAD; exit 5; }
fi

if [ ! -d "$PROJ/Assets" ]; then
  "$UNITY" -batchmode -nographics -quit -createProject "$PROJ" -logFile /content/tmpl_create.log || { echo CREATE_FAILED; exit 6; }
  echo CREATE_PROJECT_OK
else
  echo PROJECT_EXISTS
fi

echo "=== WRITE UNITY6 MANIFEST (BEFORE EDITOR OPENS PROJECT) ==="
mkdir -p "$PROJ/Packages"
python3 - "$PROJ/Packages/manifest.json" <<'PYEOF'
import json, sys
deps = {
    "com.unity.ugui": "2.0.0",
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

echo "=== IMPORT PACKAGE (tolerant: rc may reflect compile errors, assets still land) ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -importPackage "$PKG" -logFile /content/tmpl_import.log
echo "IMPORT_RC=$?"
test -d "$PROJ/Assets/ThirdPersonCoverShooter" && echo TMPL_DIR_OK || { echo TMPL_DIR_MISSING; exit 6; }
echo "CS_COUNT=$(find "$PROJ/Assets/ThirdPersonCoverShooter" -name '*.cs' | wc -l)"

echo "=== MANIFEST AGAIN (package overwrites Packages/manifest.json on import) ==="
python3 - "$PROJ/Packages/manifest.json" <<'PYEOF'
import json, sys
deps = {
    "com.unity.ugui": "2.0.0",
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

echo "=== COMPILE GATE ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -logFile /content/tmpl_compile.log
echo "COMPILE_RC=$?"
ERRS=$(grep -cE "error CS" /content/tmpl_compile.log)
echo "CS_ERRORS=$ERRS"
if [ "$ERRS" != 0 ]; then
  echo COMPILE_GATE_FAILED
  grep -E "error CS" /content/tmpl_compile.log | sed -E 's/^.*Assets/Assets/' | sort -u | head -25
  exit 6
fi
echo COMPILE_GATE_OK

echo "=== BUILD SCRIPT ==="
mkdir -p "$PROJ/Assets/Editor"
cat > "$PROJ/Assets/Editor/TemplateBuild.cs" << 'CSEOF'
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

public class TemplateBuild {
    public static void Perform() {
        string scene = "Assets/ThirdPersonCoverShooter/Scenes/Third person cover.unity";
        if (!File.Exists(scene)) {
            Debug.LogError("MISSING_SCENE " + scene);
            EditorApplication.Exit(6);
        }
        PlayerSettings.companyName = "VoyagerScrolls";
        PlayerSettings.productName = "CoverShooterPrototype";
        Directory.CreateDirectory("Builds/Win");
        var opts = new BuildPlayerOptions {
            scenes = new string[] { scene },
            locationPathName = "Builds/Win/CoverShooterPrototype.exe",
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

echo "=== BUILD WINDOWS ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod TemplateBuild.Perform -logFile /content/tmpl_build.log
BRC=$?
echo "BUILD_RC=$BRC"
grep -nE "BUILD_RESULT|MISSING_SCENE" /content/tmpl_build.log | head -5
if [ "$BRC" != 0 ]; then
  echo TMPL_BUILD_FAILED
  grep -E "error CS|Exception|Error building" /content/tmpl_build.log | head -15
  exit 6
fi
test -f "$PROJ/Builds/Win/CoverShooterPrototype.exe" || { echo NO_EXE; ls -la "$PROJ/Builds/Win" 2>&1; exit 6; }

echo "=== STAGE ==="
rm -f "$OUT"
cd "$PROJ/Builds/Win" && zip -qr "$OUT" .
mkdir -p "$DRIVE_OUT"
cp "$OUT" "$DRIVE_OUT/tmpl-win-$STAMP.zip"
echo "TMPL_BUNDLE_SIZE=$(du -sh "$OUT" | cut -f1)"
echo "TMPL_ZIP=tmpl-win-$STAMP.zip"
echo TMPL_STAGED_OK
