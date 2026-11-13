#!/bin/bash
# gm_search9.sh — get bl_DeathZone Awake full (lines 27-45)
sed -n '27,45p' $(find /content/work/mfps -name "bl_DeathZone.cs" | head -1)