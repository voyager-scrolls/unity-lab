#!/bin/bash
# mcp_head8.sh — read ManageScene.cs load handling (lines 230-290, 380-430)
echo "=== HANDLE COMMAND START ==="
sed -n '160,290p' /content/work/mfps/Library/PackageCache/com.coplaydev.unity-mcp@4384f8b518e8/Editor/Tools/ManageScene.cs
echo "=== LOAD SCENE IMPL ==="
sed -n '375,440p' /content/work/mfps/Library/PackageCache/com.coplaydev.unity-mcp@4384f8b518e8/Editor/Tools/ManageScene.cs