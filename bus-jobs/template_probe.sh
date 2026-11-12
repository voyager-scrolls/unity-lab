#!/bin/bash
# template_probe.sh - what does this VM actually have for a template import?
UNITY=/content/ue/Editor/Unity
PEMB=/content/ue/Editor/Data/PlaybackEngines

echo "=== UNITY BIN ==="
cat /content/unity_bin.txt 2>&1
test -x "$UNITY" && echo EDITOR_OK || echo NO_EDITOR
ls -la "$UNITY" 2>&1 | head -3

echo "=== PLAYBACK ENGINES (build targets) ==="
ls "$PEMB" 2>&1

echo "=== LICENSE ==="
ls -la /root/.local/share/unity3d/Unity/ 2>&1 | head -5
ls -la /content/.local/share/unity3d/Unity/ 2>&1 | head -5

echo "=== DRIVE CACHE ==="
ls -la /content/drive/MyDrive/unity-lab/cache/ 2>&1 | head -25

echo "=== TEMPLATES DIR ==="
ls -la /content/drive/MyDrive/unity-lab/templates/ 2>&1

echo "=== WORK PROJECTS ==="
ls -la /content/work/ 2>&1

echo "=== DISK ==="
df -h /content | tail -1
echo "=== RAM ==="
free -g | head -2
echo PROBE_DONE
