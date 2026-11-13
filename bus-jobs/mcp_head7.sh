#!/bin/bash
# mcp_head7.sh — read ExecuteCode.cs + check if McpBridge.cs exists
echo "=== MCPBRIDGE EXISTS? ==="
ls -la /content/work/mfps/Assets/Editor/McpBridge.cs 2>&1
echo "=== EXECUTE CODE ==="
sed -n '1,120p' /content/work/mfps/Library/PackageCache/com.coplaydev.unity-mcp@4384f8b518e8/Editor/Tools/ExecuteCode.cs
echo "=== MANAGE SCENE load_scene ==="
grep -n "load_scene\|LoadScene\|case \"load" /content/work/mfps/Library/PackageCache/com.coplaydev.unity-mcp@4384f8b518e8/Editor/Tools/ManageScene.cs