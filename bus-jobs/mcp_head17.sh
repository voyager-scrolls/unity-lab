#!/bin/bash
# mcp_head17.sh — find McpBridge.cs on VM; check McpBridge dispatch
echo "=== FIND MCPBRIDGE ==="
find /content/work/mfps -name "McpBridge.cs" 2>/dev/null
echo "=== FIND MCPBRIDGE ANYWHERE ==="
find / -name "McpBridge*" 2>/dev/null | head -10
echo "=== CHECK ASSETS/EDITOR ==="
ls -la /content/work/mfps/Assets/Editor/ 2>/dev/null || echo "NO EDITOR DIR"
echo "=== CHECK IF MCPBRIDGE IS IN PACKAGE CACHE ==="
grep -rl "class McpBridge" /content/work/mfps/ 2>/dev/null | head -5