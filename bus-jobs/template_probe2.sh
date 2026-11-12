#!/bin/bash
U=/content/ue/Editor/Unity
P=/content/ue/Editor/Data/PlaybackEngines
test -x "$U" && echo EDITOR_OK || echo NO_EDITOR
echo "PEMB:"; ls "$P" 2>&1 | tr "\n" " "; echo
echo "LIC:"; ls /root/.local/share/unity3d/Unity/ 2>&1 | tr "\n" " "; echo
test -d "$P/WindowsStandaloneSupport" && echo WIN_OK || echo WIN_MISSING
test -d "$P/WebGLSupport" && echo WEBGL_OK || echo WEBGL_MISSING
echo DONE2
