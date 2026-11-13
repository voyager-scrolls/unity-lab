#!/bin/bash
# gm_search21.sh — get bl_UIReferences Instance/Awake
grep -n "Instance\|Awake\|OnEnable\|class bl_UIReferences" $(find /content/work/mfps -name "bl_UIReferences.cs" | head -1)