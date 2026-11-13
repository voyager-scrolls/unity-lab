#!/bin/bash
# gm_search2.sh — read ManageAsset.cs to find search parameters
grep -n "search\|Search\|query\|Query\|filter\|Filter\|type\|Type" /content/work/mfps/Library/PackageCache/com.coplaydev.unity-mcp@4384f8b518e8/Editor/Tools/ManageAsset.cs | head -40