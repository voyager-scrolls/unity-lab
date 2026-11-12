#!/bin/bash
echo "HOME=$HOME  USER=$(whoami)"
echo "=== ULF SEARCH ==="
find / -maxdepth 6 -name "*.ulf" 2>/dev/null | head -5
echo "=== LICENSE DIRS ==="
ls -la "$HOME/.local/share/unity3d/Unity/" 2>&1 | head -5
ls -la /content/.local/share/unity3d/Unity/ 2>&1 | head -5
echo "=== PREVIOUS PROJECT STATE ==="
ls /content/work/runandgun/Builds 2>&1
ls /content/work/runandgun/Library 2>&1 | head -3
echo "=== BOOT LOGS ==="
ls -la /content/*.log /content/*.txt 2>/dev/null | head -10
echo DONE3
