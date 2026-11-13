#!/bin/bash
# gm_search7.sh — read bl_DeathZone.cs to understand NRE
find /content/work/mfps -name "bl_DeathZone.cs" 2>/dev/null
echo "---"
cat $(find /content/work/mfps -name "bl_DeathZone.cs" 2>/dev/null | head -1)