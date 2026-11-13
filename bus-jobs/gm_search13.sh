#!/bin/bash
# gm_search13.sh — find CollectSources signature in Unity 6
grep -rn "CollectSources" /content/ue/Editor/Data/Managed/UnityEngine.AI.NavMeshModule.dll 2>/dev/null | head -5
find /content -name "NavMeshBuilder.cs" 2>/dev/null | head -3
# Try monodis or strings
strings /content/ue/Editor/Data/Managed/UnityEngine.AI.NavMeshModule.dll 2>/dev/null | grep -i "CollectSources" | head -5