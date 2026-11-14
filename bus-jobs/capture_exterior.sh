#!/bin/bash
# capture_exterior.sh - cinematic exterior set: cordon, squads, vehicles, facade.
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
STAMP=$(date +%s)

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/HeistLevel.unity" || { echo NO_SCENE; exit 6; }
echo PREFLIGHT_OK

command -v xvfb-run >/dev/null 2>&1 && echo XVFB_OK || { echo XVFB_MISSING; exit 6; }

mkdir -p "$PROJ/Assets/Editor" /content/shots7
cat > "$PROJ/Assets/Editor/CaptureExterior.cs" << 'CSEOF'
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class CaptureExterior
{
    public static void Capture()
    {
        EditorSceneManager.OpenScene("Assets/MFPS/Scenes/HeistLevel.unity", OpenSceneMode.Single);
        Directory.CreateDirectory("/content/shots7");
        int W = 1280;
        int H = 720;
        var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32);

        var camGo = new GameObject("CaptureCamExterior");
        var cam = camGo.AddComponent<Camera>();
        cam.nearClipPlane = 0.08f;
        cam.farClipPlane = 300f;
        cam.targetTexture = rt;

        Vector3[] pos = new Vector3[]
        {
            new Vector3(0f, 2.2f, -20f),
            new Vector3(-12f, 1.7f, -12f),
            new Vector3(12f, 1.7f, -14f),
            new Vector3(0f, 1.6f, -6.2f),
            new Vector3(0f, 1.7f, -14f)
        };
        Vector3[] look = new Vector3[]
        {
            new Vector3(0f, 3.0f, 0f),
            new Vector3(0f, 2.2f, -2f),
            new Vector3(0f, 2.0f, -3f),
            new Vector3(-3.2f, 1.1f, -2.6f),
            new Vector3(0f, 7.6f, 1.2f)
        };
        float[] fov = new float[] { 60f, 65f, 65f, 46f, 55f };

        for (int i = 0; i < pos.Length; i++)
        {
            cam.fieldOfView = fov[i];
            camGo.transform.position = pos[i];
            camGo.transform.LookAt(look[i], Vector3.up);
            RenderAndSave(cam, rt, W, H, "/content/shots7/ex_" + i + ".png");
        }

        Debug.Log("CAPTURE_DONE 5");
    }

    static void RenderAndSave(Camera cam, RenderTexture rt, int w, int h, string path)
    {
        cam.Render();
        RenderTexture.active = rt;
        var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
        tex.Apply();
        File.WriteAllBytes(path, tex.EncodeToPNG());
        Object.DestroyImmediate(tex);
    }
}
CSEOF
echo CAPTURE_SCRIPT_WRITTEN

rm -rf "$PROJ/Temp"
mkdir -p /tmp/xdg; chmod 700 /tmp/xdg
export XDG_RUNTIME_DIR=/tmp/xdg

xvfb-run -a -s "-screen 0 1280x720x24" "$UNITY" -batchmode -quit -projectPath "$PROJ" -executeMethod CaptureExterior.Capture -logFile /content/capture_ex.log 2>&1 || true
if grep -q "Aborting batchmode" /content/capture_ex.log 2>/dev/null; then
  echo CAPTURE_FAIL
  grep -n "error CS\|Exception\|Aborting" /content/capture_ex.log | head -15
  exit 6
fi
grep -n "CAPTURE_DONE" /content/capture_ex.log | tail -1
SHOTS=$(ls /content/shots7/*.png 2>/dev/null | wc -l)
echo "SHOTS=$SHOTS"
test "$SHOTS" -ge 5 || { echo TOO_FEW_SHOTS; tail -20 /content/capture_ex.log; exit 6; }
mkdir -p "/content/drive/MyDrive/unity-lab/screenshots/${STAMP}_exterior"
cp /content/shots7/*.png "/content/drive/MyDrive/unity-lab/screenshots/${STAMP}_exterior/" && echo SHOTS_STAGED
echo "SCREENSHOT_DIR=${STAMP}_exterior"
echo CAPTURE_COMPLETE
