#!/bin/bash
# pull contra build log errors
grep -nE "error CS|Error CS|error TS|Aborting" /content/build_contra.log | head -30
echo ---
grep -B2 -A4 "error CS" /content/build_contra.log | head -60
echo ---
ls /content/work/runandgun/Assets/Contra/ /content/work/runandgun/Assets/Editor/ 2>&1
echo LOG_DONE
