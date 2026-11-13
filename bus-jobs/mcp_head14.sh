#!/bin/bash
# mcp_head14.sh — read ToSceneCommand full (lines 90-115) + get_hierarchy params
grep -n "scope\|depth\|pageSize\|cursor\|GetHierarchy\|GetRoots\|GetChildren" /content/work/mfps/Library/PackageCache/com.coplaydev.unity-mcp@4384f8b518e8/Editor/Tools/ManageScene.cs | head -30