#!/bin/bash
# template_import_build.sh - Asset Store .unitypackage -> Windows standalone build.
# Handles: licence install from Drive, Windows build module (.pkg recipe), 2018-era
# manifest replacement after import, Unity-6 upgrade of serialized assets.
set -u

UNITY=/content/ue/Editor/Unity
PEMB=/content/ue/Editor/Data/PlaybackEngines
PROJ=/content/work/tmpl
PKG=/content/drive/MyDrive/unity-lab/templates/covershooter-1.6.2.unitypackage
SCENE="Assets/ThirdPersonCoverShooter/Scenes/Third person cover.unity"
STAMP=$(date +%s)
OUT=/content/tmpl-win.zip
DRIVE_OUT=/content/drive/MyDrive/unity-lab/builds
WPKG=/content/drive/MyDrive/unity-lab/cache/Windows.pkg
WURL="https://download.unity3d.com/download_unity/e35f0c77bd8e/MacEditorTargetInstaller/UnitySetup-Windows-Mono-Support-for-Editor-6000.3.10f1.pkg"

echo "=== PREFLIGHT ==="
test -f /content/unity_bin.txt || { echo NO_UNITY_BIN; exit 6; }
test -x "$UNITY" || { echo NO_EDITOR_BIN; exit 6; }
echo PREFLIGHT_OK

echo "=== WAIT FOR PACKAGE ==="
for i in $(seq 1 30); do
  if [ -s "$PKG" ]; then echo PKG_VISIBLE; break; fi
  echo "PKG_WAITING $i"; sleep 20
done
test -s "$PKG" || { echo NO_PACKAGE; exit 6; }

echo "=== LICENCE ==="
mkdir -p "$HOME/.local/share/unity3d/Unity"
if [ -f /content/drive/MyDrive/unity-lab/secrets/Unity_lic.ulf ]; then
  cp /content/drive/MyDrive/unity-lab/secrets/Unity_lic.ulf "$HOME/.local/share/unity3d/Unity/Unity_lic.ulf"
  chmod 600 "$HOME/.local/share/unity3d/Unity/Unity_lic.ulf"
  echo ULF_INSTALLED
else
  echo ULF_MISSING_CONTINUE
fi

echo "=== ENSURE WINDOWS MODULE ==="
if [ -f "$PEMB/WindowsStandaloneSupport/UnityEditor.WindowsStandalone.Extensions.dll" ]; then
  echo WIN_MODULE_PRESENT
else
  if [ ! -s "$WPKG" ]; then
    echo WIN_PKG_DOWNLOAD
    aria2c --allow-overwrite=true -x8 -d /content -o Windows.pkg "$WURL" || { echo WIN_DL_FAIL; exit 5; }
    cp /content/Windows.pkg "$WPKG" 2>/dev/null || true
    WPKG=/content/Windows.pkg
  fi
  rm -rf /content/pkgx1 /content/pkgx2; mkdir -p /content/pkgx1 /content/pkgx2
  7z x -y "$WPKG" -o/content/pkgx1 >/dev/null || { echo WIN_7Z_FAIL; exit 5; }
  PAY=$(ls /content/pkgx1 | grep -i '^payload' | head -1)
  [ -n "$PAY" ] || { echo WIN_NO_PAYLOAD; ls /content/pkgx1; exit 5; }
  7z x -y "/content/pkgx1/$PAY" -o/content/pkgx2 >/dev/null || { echo WIN_PAYLOAD_7Z_FAIL; exit 5; }
  SRC=/content/pkgx2
  while true; do
    N=$(ls "$SRC" | wc -l)
    E=$(ls "$SRC" | head -1)
    if [ "$N" = 1 ] && [ -d "$SRC/$E" ] && [ "$E" != "WindowsStandaloneSupport" ]; then SRC="$SRC/$E"; else break; fi
  done
  mkdir -p "$PEMB/WindowsStandaloneSupport"
  cp -a "$SRC/." "$PEMB/WindowsStandaloneSupport/"
  [ -f "$PEMB/WindowsStandaloneSupport/UnityEditor.WindowsStandalone.Extensions.dll" ] && echo WIN_MODULE_INSTALLED || { echo WIN_MODULE_LAYOUT_UNEXPECTED; ls "$PEMB/WindowsStandaloneSupport" | head; exit 5; }
fi

if [ ! -d "$PROJ/Assets" ]; then
  echo "=== CREATE PROJECT ==="
  "$UNITY" -batchmode -nographics -quit -createProject "$PROJ" -logFile /content/tmpl_create.log || { echo CREATE_FAILED; tail -25 /content/tmpl_create.log; exit 6; }
  echo CREATE_PROJECT_OK
else
  echo PROJECT_EXISTS
fi
cp "$PROJ/Packages/manifest.json" /content/tmpl_manifest_default.json 2>/dev/null || true

echo "=== IMPORT PACKAGE ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -importPackage "$PKG" -logFile /content/tmpl_import.log
IRC=$?
echo "IMPORT_RC=$IRC"
if [ "$IRC" != 0 ]; then
  echo IMPORT_FAILED
  grep -nE "error CS|No valid Unity Editor license|Exception|Failed to" /content/tmpl_import.log | head -25
  exit 6
fi
test -d "$PROJ/Assets/ThirdPersonCoverShooter" && echo TMPL_DIR_OK || { echo TMPL_DIR_MISSING; exit 6; }

echo "=== RESTORE UNITY6 MANIFEST ==="
if [ -s /content/tmpl_manifest_default.json ]; then
  cp /content/tmpl_manifest_default.json "$PROJ/Packages/manifest.json"
  echo MANIFEST_RESTORED
fi
rm -f "$PROJ/Packages/packages-lock.json"

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
echo BUILD_SCRIPT_WRITTEN

echo "=== BUILD WINDOWS ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod TemplateBuild.Perform -logFile /content/tmpl_build.log
BRC=$?
echo "BUILD_RC=$BRC"
grep -nE "error CS|BUILD_RESULT|MISSING_SCENE|No valid Unity Editor license" /content/tmpl_build.log | head -30
if [ "$BRC" != 0 ]; then
  echo TMPL_BUILD_FAILED
  grep -nE "error CS|Exception|Error building|license" /content/tmpl_build.log | head -25
  exit 6
fi
test -f "$PROJ/Builds/Win/CoverShooterPrototype.exe" || { echo NO_EXE; ls -la "$PROJ/Builds/Win" 2>&1; exit 6; }

echo "=== STAGE ==="
rm -f "$OUT"
cd "$PROJ/Builds/Win" && zip -qr "$OUT" .
mkdir -p "$DRIVE_OUT"
cp "$OUT" "$DRIVE_OUT/tmpl-win-$STAMP.zip"
SZ=$(du -sh "$OUT" | cut -f1)
echo "TMPL_BUNDLE_SIZE=$SZ"
echo "TMPL_STAGED_OK"
echo "TMPL_ZIP=tmpl-win-$STAMP.zip"
