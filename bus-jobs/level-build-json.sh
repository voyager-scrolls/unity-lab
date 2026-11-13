#!/bin/bash
# level-build-json.sh — build a Heist level from a pre-generated LevelLayout Asset
# Requires: MFPS project already set up on VM (run heist-catalog-build.sh first)
set -e

MFPSROOT=/content/drive/MyDrive/unity-lab
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
UNITY_BIN=/content/unity_bin.txt

echo "=== PREFLIGHT ==="
test -f "$UNITY_BIN" || { echo NO_UNITY_BIN; exit 6; }
test -x "$UNITY" || { echo NO_EDITOR_BIN; exit 6; }
test -d "$PROJ/Assets/MFPS" || { echo NO_PROJECT; exit 6; }
echo PREFLIGHT_OK

echo "=== GENERATE LEVEL LAYOUT ASSET ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod LevelLayoutGenerator.Generate -logFile /content/levellayout_gen.log 2>&1
GEN_RC=$?
echo "GENERATE_RC=$GEN_RC"
if [ "$GEN_RC" != "0" ]; then
  echo "GENERATE_FAILED"
  tail -10 /content/levellayout_gen.log
  exit 6
fi
echo "GENERATE_OK"

echo "=== BUILD LEVEL FROM ASSET ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod LevelBuilder.BuildFromLayoutAsset -logFile /content/level_build.log 2>&1
BUILD_RC=$?
echo "BUILD_RC=$BUILD_RC"
CS_ERRORS=$(grep -c "error CS" /content/level_build.log 2>/dev/null || true)
echo "CS_ERRORS=$CS_ERRORS"
if [ "$CS_ERRORS" != "0" ]; then
  echo "COMPILE_GATE_FAIL"
  grep -n "error CS" /content/level_build.log | head -20
  exit 6
fi
if [ "$BUILD_RC" != "0" ]; then
  echo "LEVEL_BUILD_FAIL"
  tail -20 /content/level_build.log
  exit 6
fi
echo "LEVEL_BUILD_OK"

echo "=== BUILD WINDOWS ==="
cat > "$PROJ/Assets/Editor/MfpsBuild.cs" << 'CSEOF'
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

public static class MfpsBuild
{
    [MenuItem("Tools/Build Windows")]
    public static void BuildWindows()
    {
        string outDir = "Builds/Win";
        Directory.CreateDirectory(outDir);
        string exePath = Path.Combine(outDir, "MFPSPrototype.exe");

        BuildPlayerOptions opts = new BuildPlayerOptions();
        opts.scenes = new[] { "Assets/MFPS/Scenes/HeistLevel.unity" };
        opts.locationPathName = exePath;
        opts.target = BuildTarget.StandaloneWindows64;
        opts.options = BuildOptions.None;

        BuildReport report = BuildPipeline.BuildPlayer(opts);
        if (report.summary.result != BuildResult.Succeeded)
        {
            Debug.LogError("BUILD_FAILED: " + report.summary.result);
            foreach (var step in report.steps)
                foreach (var msg in step.messages)
                    if (msg.type == LogType.Error)
                        Debug.LogError("BUILD_MSG " + msg.type + " " + msg.content);
            throw new System.Exception("BUILD_FAILED: " + report.summary.result);
        }
        Debug.Log("BUILD_RESULT Succeeded errors=" + report.summary.totalErrors + " warnings=" + report.summary.totalWarnings + " size=" + report.summary.totalSize);
    }
}
CSEOF

"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod MfpsBuild.BuildWindows -logFile /content/win_build.log 2>&1
WIN_RC=$?
echo "WIN_BUILD_RC=$WIN_RC"
WIN_ERRORS=$(grep -c "error CS" /content/win_build.log 2>/dev/null || true)
echo "WIN_CS_ERRORS=$WIN_ERRORS"
if [ "$WIN_RC" != "0" ] || [ "$WIN_ERRORS" != "0" ]; then
  echo "WIN_BUILD_FAIL"
  grep -n "error CS\|BUILD_FAILED\|BUILD_RESULT" /content/win_build.log | head -20
  exit 6
fi
grep -n "BUILD_RESULT" /content/win_build.log | tail -1

echo "=== STAGE ==="
STAMP=$(date +%s)
BUNDLE="$PROJ/Builds/Win"
if [ ! -f "$BUNDLE/MFPSPrototype.exe" ]; then echo "NO_EXE"; exit 6; fi
cd "$PROJ" && zip -qr "/tmp/mfps-level-$STAMP.zip" "Builds/Win" && echo "ZIPPED"
ls -lh "/tmp/mfps-level-$STAMP.zip"
cp "/tmp/mfps-level-$STAMP.zip" "$MFPSROOT/builds/mfps-level-$STAMP.zip" && echo "STAGED_OK"
echo "MFPS_LEVEL_ZIP=mfps-level-$STAMP.zip"
echo "LEVEL_BUILD_COMPLETE"