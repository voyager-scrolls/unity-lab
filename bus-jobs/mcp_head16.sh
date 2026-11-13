#!/bin/bash
# mcp_head16.sh — check McpBridge.cs dispatch cases + ExecuteCode.cs full HandleCommand
echo "=== MCPBRIDGE DISPATCH ==="
grep -n "case\|execute_code\|ExecuteCode" /content/work/mfps/Assets/Editor/McpBridge.cs 2>/dev/null || echo "MCPBRIDGE NOT FOUND"
echo "=== EXECUTE CODE FULL ==="
sed -n '1,120p' /content/work/mfps/Library/PackageCache/com.coplaydev.unity-mcp@4384f8b518e8/Editor/Tools/ExecuteCode.cs