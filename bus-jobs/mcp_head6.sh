#!/bin/bash
# mcp_head6.sh — find execute_code handler in MCPForUnity source + check McpBridge.cs
echo "=== MCPBRIDGE.CS ON VM ==="
cat /content/work/mfps/Assets/Editor/McpBridge.cs 2>/dev/null || echo "NOT FOUND"
echo "=== SEARCH execute_code IN PACKAGE CACHE ==="
grep -rl "execute_code" /content/work/mfps/Library/PackageCache/ 2>/dev/null | head -5
echo "=== SEARCH ExecuteCode HANDLER ==="
grep -rn "class ExecuteCode\|HandleCommand" /content/work/mfps/Library/PackageCache/com.coplaydev.unity-mcp*/Editor/Tools/ 2>/dev/null | head -20