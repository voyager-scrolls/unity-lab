#!/bin/bash
# gm_search22.sh — get bl_UIReferences Instance property
sed -n '1225,1245p' $(find /content/work/mfps -name "bl_UIReferences.cs" | head -1)