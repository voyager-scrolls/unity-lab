#!/bin/bash
# gm_search16.sh — get Instance property + Awake + RegisterSpawnPoint
sed -n '830,860p' $(find /content/work/mfps -name "bl_GameManager.cs" | head -1)
echo "---REGISTER---"
sed -n '470,490p' $(find /content/work/mfps -name "bl_GameManager.cs" | head -1)