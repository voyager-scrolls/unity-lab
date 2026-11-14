#!/bin/bash
# capture_street.sh - verification views for the street bank level.
# 8 eye-level/overview views + topdown, staged to Drive screenshots/<stamp>_street/.
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
STAMP=$(date +%s)

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/HeistLevel.unity" || { echo NO_SCENE; exit 6; }
echo PREFLIGHT_OK

command -v xvfb-run >/dev/null 2>&1 && echo XVFB_OK || { echo XVFB_MISSING; exit 6; }

mkdir -p "$PROJ/Assets/Editor" /content/shots_street
cat > "$PROJ/Assets/Editor/CaptureStreet.cs" << 'CSEOF'
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class CaptureStreet
{
    public static void Capture()
    {
        EditorSceneManager.OpenScene("Assets/MFPS/Scenes/HeistLevel.unity", OpenSceneMode.Single);
        Directory.CreateDirectory("/content/shots_street");
        int W = 1280;
        int H = 720;
        var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32);

        var camGo = new GameObject("CaptureCamStreet");
        var cam = camGo.AddComponent<Camera>();
        cam.fieldOfView = 62f;
        cam.nearClipPlane = 0.08f;
        cam.farClipPlane = 320f;
        cam.targetTexture = rt;

        Vector3[] pos = new Vector3[]
        {
            new Vector3(0f, 2.4f, -34f),
            new Vector3(-7f, 1.8f, -11f),
            new Vector3(-19f, 2.2f, -25f),
            new Vector3(19f, 2.2f, -25f),
            new Vector3(-30f, 1.7f, -20f),
            new Vector3(0f, 1.7f, 1.5f),
            new Vector3(0f, 1.7f, 9.5f),
            new Vector3(0f, 1.75f, -5.5f)
        };
        Vector3[] look = new Vector3[]
        {
            new Vector3(0f, 5f, 0f),
            new Vector3(0f, 3.2f, 0f),
            new Vector3(0f, 1.4f, -12f),
            new Vector3(0f, 1.4f, -12f),
            new Vector3(10f, 1.6f, -20f),
            new Vector3(0f, 1.7f, 14f),
            new Vector3(0f, 1.2f, 14.5f),
            new Vector3(0f, 6f, 0f)
        };
        float[] fov = new float[] { 55f, 60f, 62f, 62f, 60f, 62f, 55f, 65f };

        for (int i = 0; i < pos.Length; i++)
        {
            cam.fieldOfView = fov[i];
            camGo.transform.position = pos[i];
            camGo.transform.LookAt(look[i], Vector3.up);
            RenderAndSave(cam, rt, W, H, "/content/shots_street/st_" + i + ".png");
        }

        cam.orthographic = true;
        cam.orthographicSize = 46f;
        cam.fieldOfView = 62f;
        camGo.transform.position = new Vector3(0f, 70f, -22f);
        camGo.transform.rotation = Quaternion.Euler(90f, 0f, 0f);
        RenderAndSave(cam, rt, W, H, "/content/shots_street/topdown.png");

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

xvfb-run -a -s "-screen 0 1280x720x24" "$UNITY" -batchmode -quit -projectPath "$PROJ" -executeMethod CaptureStreet.Capture -logFile /content/capture_street.log 2>&1 || true
if grep -q "Aborting batchmode" /content/capture_street.log 2>/dev/null; then
  echo CAPTURE_FAIL
  grep -n "error CS\|Exception\|Aborting" /content/capture_street.log | head -15
  exit 6
fi
grep -n "CAPTURE_DONE" /content/capture_street.log | tail -1
SHOTS=$(ls /content/shots_street/*.png 2>/dev/null | wc -l)
echo "SHOTS=$SHOTS"
test "$SHOTS" -ge 5 || { echo TOO_FEW_SHOTS; tail -20 /content/capture_street.log; exit 6; }
mkdir -p "/content/drive/MyDrive/unity-lab/screenshots/${STAMP}_street"
cp /content/shots_street/*.png "/content/drive/MyDrive/unity-lab/screenshots/${STAMP}_street/" && echo SHOTS_STAGED
echo "SCREENSHOT_DIR=${STAMP}_street"
echo CAPTURE_COMPLETE
