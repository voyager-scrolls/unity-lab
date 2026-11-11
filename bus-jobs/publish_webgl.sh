#!/bin/bash
# publish_webgl.sh — stage the VM's built WebGL bundle to Drive staging (PC pulls to docs/webgl/ for Pages)
set -e
SRC=/content/work/demo/Builds/WebGL/probe
if [ ! -f "$SRC/index.html" ]; then echo NO_BUNDLE; exit 6; fi
DST=/content/drive/MyDrive/unity-lab/pages-staging/webgl
rm -rf "$DST"
mkdir -p "$DST"
cp -a "$SRC/." "$DST/"
echo STAGED_FILES=$(ls "$DST" | wc -l)
du -sh "$DST"
echo PUBLISH_STAGED_OK
