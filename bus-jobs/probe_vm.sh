#!/bin/bash
# probe_vm.sh - state check of current VM (prepared vs cold)
echo "UNITY_BIN: $(cat /content/unity_bin.txt 2>/dev/null || echo MISSING)"
test -x /content/ue/Editor/Unity && echo EDITOR_PRESENT || echo EDITOR_MISSING
test -d /content/work/demo/Assets && echo DEMO_PRESENT || echo DEMO_MISSING
test -d /content/ue/Editor/Data/PlaybackEngines/WebGLSupport && echo WEBGL_MODULE_PRESENT || echo WEBGL_MODULE_MISSING
test -s /content/drive/MyDrive/unity-lab/cache/WebGL.tar.xz && echo WEBGL_TARBALL_CACHED || echo WEBGL_TARBALL_NOT_CACHED
LC=/content/ue/Editor/Data/Resources/Licensing/Client/Unity.Licensing.Client
if [ -x "$LC" ]; then
  "$LC" --show-seats 2>&1 | head -3
else
  echo LICENSING_CLIENT_MISSING
fi
ls /content/work/ 2>/dev/null
echo PROBE_DONE
