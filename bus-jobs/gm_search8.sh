#!/bin/bash
# gm_search8.sh — get bl_DeathZone Awake + KillZoneUI field
grep -n "KillZoneUI\|Awake\|OnEnable\|bl_UIReferences\|LocalPlayerViewID\|class bl_DeathZone" /content/work/mfps/Assets/MFPS/Scripts/GamePlay/bl_DeathZone.cs 2>/dev/null || find /content/work/mfps -name "bl_DeathZone.cs" -exec grep -n "KillZoneUI\|Awake\|OnEnable\|bl_UIReferences\|LocalPlayerViewID\|class bl_DeathZone" {} \;