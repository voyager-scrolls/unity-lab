#!/bin/bash
# publish_webgl_full.sh - self-sufficient: rebuild WebGL bundle if missing, then stage to pages-staging
UNITY=/content/ue/Editor/Unity
PEMB=/content/ue/Editor/Data/PlaybackEngines
CS=/content/work/demo/Assets/Editor/BuildScript.cs
PROJ=/content/work/demo
BUNDLE=$PROJ/Builds/WebGL/probe

echo "=== BUNDLE CHECK ==="
if [ -f "$BUNDLE/index.html" ]; then
  echo BUNDLE_PRESENT
else
  echo "=== BUNDLE MISSING - REBUILDING ==="
  echo "--- PREFLIGHT ---"
  test -f /content/unity_bin.txt || { echo NO_UNITY_BIN; exit 6; }
  test -f "$CS" || { echo NO_BUILDSCRIPT; exit 6; }
  test -x "$UNITY" || { echo NO_EDITOR_BIN; exit 6; }
  echo PREFLIGHT_OK
  echo "--- ENSURE WEBGL MODULE ---"
  if [ -d "$PEMB/WebGLSupport" ]; then
    echo WEBGL_MODULE_PRESENT
  else
    TARB=/content/drive/MyDrive/unity-lab/cache/WebGL.tar.xz
    WURL="https://download.unity3d.com/download_unity/e35f0c77bd8e/LinuxEditorTargetInstaller/UnitySetup-WebGL-Support-for-Editor-6000.3.10f1.tar.xz"
    if [ ! -s "$TARB" ]; then
      echo NO_CACHE_TARBALL_CDN_FALLBACK
      aria2c --allow-overwrite=true -x8 -d /content -o webgl_mod.tar.xz "$WURL" || { echo CDN_DL_FAIL; exit 5; }
      cp /content/webgl_mod.tar.xz "$TARB" 2>/dev/null || true
      TARB=/content/webgl_mod.tar.xz
    fi
    md5sum "$TARB" | grep -q 74706376db4dd2202532a0d71824a793 || { echo WEB_MD5_FAIL; exit 5; }
    tar -xJf "$TARB" -C /content/ue || { echo EXTRACT_FAIL; exit 5; }
    test -d "$PEMB/WebGLSupport" && echo WEBGL_MODULE_EXTRACTED || { echo MODULE_DIR_MISSING; exit 5; }
  fi
  echo "--- LIBRARY CACHE RESTORE ---"
  if [ ! -d "$PROJ/Library" ] && [ -s /content/drive/MyDrive/unity-lab/cache/library-demo.tar.gz ]; then
    mkdir -p "$PROJ"
    tar xzf /content/drive/MyDrive/unity-lab/cache/library-demo.tar.gz -C "$PROJ" && echo LIBRARY_RESTORED || echo LIBRARY_RESTORE_FAILED_NONFATAL
  else
    echo LIBRARY_SKIP
  fi
  echo "--- RETARGET ---"
  python3 - "$CS" <<'PYEOF'
import sys, re
p = sys.argv[1]
s = open(p).read()
s = re.sub(r'var target = BuildTarget\.\w+; var outDir = "[^"]+";',
           'var target = BuildTarget.WebGL; var outDir = "Builds/WebGL/probe";', s)
open(p, 'w').write(s)
print('RETARGETED', re.findall(r'var target = BuildTarget\.\w+', s))
PYEOF
  echo "--- BUILD ---"
  rm -rf "$PROJ/Temp"
  mkdir -p /tmp/xdg; chmod 700 /tmp/xdg
  printf 'pcm.!default { type null }\nctl.!default { type null }\n' > /etc/asound.conf
  export XDG_RUNTIME_DIR=/tmp/xdg
  cd "$PROJ" && /usr/bin/time -v "$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod BuildScript.PerformBuild -logFile /content/build_bus_webgl.log 2>/content/time_bus.txt
  RC=$?
  echo "BUILD_RC=$RC"
  grep -E 'Elapsed|Maximum resident' /content/time_bus.txt || true
  tail -5 /content/build_bus_webgl.log
  test "$RC" = 0 || { echo REBUILD_FAILED; exit 6; }
  test -f "$BUNDLE/index.html" || { echo REBUILD_DID_NOT_PRODUCE; exit 6; }
fi

echo "=== STAGE ==="
DST=/content/drive/MyDrive/unity-lab/pages-staging/webgl
rm -rf "$DST"
mkdir -p "$DST"
cp -a "$BUNDLE/." "$DST/"
echo STAGED_FILES=$(ls "$DST" | wc -l)
du -sh "$DST"
echo PUBLISH_STAGED_OK
