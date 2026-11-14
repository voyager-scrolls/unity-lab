#!/bin/bash
# capture_views.sh - renders 8 eye-level views + 1 top-down ortho of HeistLevel under Xvfb (software GL).
# Stages PNGs to Drive screenshots/<stamp>/ for shared visual review before player builds.
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
STAMP=$(date +%s)

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/HeistLevel.unity" || { echo NO_SCENE; exit 6; }
echo PREFLIGHT_OK

echo "=== ENSURE XVFB+GL ==="
if ! command -v xvfb-run >/dev/null 2>&1; then
  apt-get update -qq >/dev/null 2>&1 || true
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq xvfb libgl1-mesa-dri libglx-mesa0 libglu1-mesa >/dev/null 2>&1 || true
fi
command -v xvfb-run >/dev/null 2>&1 && echo XVFB_OK || { echo XVFB_MISSING; exit 6; }

mkdir -p "$PROJ/Assets/Editor" /content/shots
cat > "$PROJ/Assets/Editor/CaptureViews.cs" << 'CSEOF'
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class CaptureViews
{
    public static void Capture()
    {
        EditorSceneManager.OpenScene("Assets/MFPS/Scenes/HeistLevel.unity", OpenSceneMode.Single);
        Directory.CreateDirectory("/content/shots");
        int W = 1280;
        int H = 720;
        var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32);

        var camGo = new GameObject("CaptureCam");
        var cam = camGo.AddComponent<Camera>();
        cam.fieldOfView = 62f;
        cam.nearClipPlane = 0.08f;
        cam.farClipPlane = 260f;
        cam.targetTexture = rt;

        Vector3[] pos = new Vector3[]
        {
            new Vector3(0f, 1.7f, -9f),
            new Vector3(0f, 1.7f, 0.9f),
            new Vector3(0f, 1.7f, 6.5f),
            new Vector3(0f, 1.7f, 12.3f),
            new Vector3(0f, 1.7f, 16.2f),
            new Vector3(0f, 1.7f, 21.5f),
            new Vector3(-9.8f, 1.7f, 16.0f),
            new Vector3(9.8f, 1.7f, 16.0f)
        };
        Vector3[] look = new Vector3[]
        {
            new Vector3(0f, 1.7f, 4f),
            new Vector3(0f, 1.7f, 9f),
            new Vector3(0f, 1.7f, 12f),
            new Vector3(0f, 1.6f, 15f),
            new Vector3(0f, 1.6f, 22f),
            new Vector3(4.0f, 1.2f, 23f),
            new Vector3(-10f, 1.6f, 23f),
            new Vector3(10f, 1.6f, 23f)
        };

        for (int i = 0; i < pos.Length; i++)
        {
            camGo.transform.position = pos[i];
            camGo.transform.LookAt(look[i], Vector3.up);
            RenderAndSave(cam, rt, W, H, "/content/shots/view_" + i + ".png");
        }

        // top-down orthographic
        cam.orthographic = true;
        cam.orthographicSize = 28f;
        camGo.transform.position = new Vector3(0f, 60f, -0.5f);
        camGo.transform.rotation = Quaternion.Euler(90f, 0f, 0f);
        RenderAndSave(cam, rt, W, H, "/content/shots/topdown.png");

        Debug.Log("CAPTURE_DONE 9");
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

xvfb-run -a -s "-screen 0 1280x720x24" "$UNITY" -batchmode -quit -projectPath "$PROJ" -executeMethod CaptureViews.Capture -logFile /content/capture.log 2>&1 || true
if grep -q "Aborting batchmode" /content/capture.log 2>/dev/null; then
  echo CAPTURE_FAIL
  grep -n "error CS\|Exception\|Aborting" /content/capture.log | head -15
  exit 6
fi
grep -n "CAPTURE_DONE" /content/capture.log | tail -1
SHOTS=$(ls /content/shots/*.png 2>/dev/null | wc -l)
echo "SHOTS=$SHOTS"
test "$SHOTS" -ge 5 || { echo TOO_FEW_SHOTS; tail -20 /content/capture.log; exit 6; }
mkdir -p "/content/drive/MyDrive/unity-lab/screenshots/$STAMP"
cp /content/shots/*.png "/content/drive/MyDrive/unity-lab/screenshots/$STAMP/" && echo SHOTS_STAGED
echo "SCREENSHOT_DIR=$STAMP"
echo CAPTURE_COMPLETE
