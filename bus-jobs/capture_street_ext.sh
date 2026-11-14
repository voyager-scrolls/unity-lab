#!/bin/bash
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
STAMP=$(date +%s)
OUT=/content/shots_ext

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/HeistLevel.unity" || { echo NO_SCENE; exit 6; }
echo PREFLIGHT_OK

if ! command -v xvfb-run >/dev/null 2>&1; then
  (apt-get update -qq && apt-get install -y -qq xvfb libgl1-mesa-dri mesa-utils) >/dev/null 2>&1 || true
fi
command -v xvfb-run >/dev/null 2>&1 && echo XVFB_OK || { echo NO_XVFB; exit 6; }

cat > "$PROJ/Assets/Editor/CaptureStreetExt.cs" << 'CSEOF'
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class CaptureStreetExt
{
    public static void Capture()
    {
        var scene = EditorSceneManager.OpenScene("Assets/MFPS/Scenes/HeistLevel.unity");
        int W = 1280, H = 720;
        RenderTexture rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32);
        rt.Create();

        GameObject camGo = new GameObject("CaptureCam");
        Camera cam = camGo.AddComponent<Camera>();
        cam.targetTexture = rt;
        cam.nearClipPlane = 0.08f;
        cam.farClipPlane = 400f;
        cam.fieldOfView = 60f;

        Vector3[] pos = new Vector3[] {
            new Vector3(0f, 2.6f, -34f),
            new Vector3(-44f, 3.0f, -6f),
            new Vector3(44f, 3.0f, -6f),
            new Vector3(-40f, 2.0f, -20f),
            new Vector3(40f, 2.0f, -20f),
            new Vector3(-44f, 2.2f, -7f),
            new Vector3(-13f, 2.4f, -21f),
            new Vector3(13f, 2.4f, -21f),
            new Vector3(0f, 34f, 6f),
            new Vector3(0f, 3.0f, -36f)
        };
        Vector3[] look = new Vector3[] {
            new Vector3(0f, 6f, 0f),
            new Vector3(-18f, 4f, -26f),
            new Vector3(18f, 4f, -26f),
            new Vector3(40f, 3f, -20f),
            new Vector3(-40f, 3f, -20f),
            new Vector3(-8f, 3.0f, 3.5f),
            new Vector3(-26f, 1.2f, -15f),
            new Vector3(26f, 1.2f, -15f),
            new Vector3(0f, 0f, -18f),
            new Vector3(0f, 7f, 0f)
        };
        float[] fov = new float[] { 55f, 60f, 60f, 55f, 55f, 62f, 60f, 60f, 48f, 55f };

        string dir = "/content/shots_ext";
        Directory.CreateDirectory(dir);

        for (int i = 0; i < pos.Length; i++)
        {
            cam.fieldOfView = fov[i];
            camGo.transform.position = pos[i];
            camGo.transform.LookAt(look[i]);
            cam.Render();
            RenderTexture.active = rt;
            Texture2D tex = new Texture2D(W, H, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, W, H), 0, 0);
            tex.Apply();
            RenderTexture.active = null;
            File.WriteAllBytes(dir + "/ext_" + i + ".png", tex.EncodeToPNG());
            Object.DestroyImmediate(tex);
        }

        cam.orthographic = true;
        cam.orthographicSize = 80f;
        camGo.transform.position = new Vector3(0f, 90f, -14f);
        camGo.transform.rotation = Quaternion.Euler(90f, 0f, 0f);
        cam.Render();
        RenderTexture.active = rt;
        Texture2D top = new Texture2D(W, H, TextureFormat.RGB24, false);
        top.ReadPixels(new Rect(0, 0, W, H), 0, 0);
        top.Apply();
        RenderTexture.active = null;
        File.WriteAllBytes(dir + "/topdown.png", top.EncodeToPNG());
        Object.DestroyImmediate(top);

        Debug.Log("CAPTURE_DONE " + (pos.Length + 1));
    }
}
CSEOF

echo CAPTURE_SCRIPT_WRITTEN
xvfb-run -a -s "-screen 0 1280x720x24" "$UNITY" -batchmode -quit -projectPath "$PROJ" -executeMethod CaptureStreetExt.Capture -logFile /content/capture_ext.log 2>&1 || true
grep -q "CAPTURE_DONE" /content/capture_ext.log && echo CAPTURE_LOG_OK || { echo CAPTURE_LOG_FAIL; tail -5 /content/capture_ext.log; exit 6; }

SHOTS=$(ls /content/shots_ext/*.png 2>/dev/null | wc -l)
echo "SHOTS=$SHOTS"
if [ "$SHOTS" -lt 6 ]; then echo TOO_FEW_SHOTS; exit 6; fi

mkdir -p "/content/drive/MyDrive/unity-lab/screenshots/${STAMP}_ext"
cp /content/shots_ext/*.png "/content/drive/MyDrive/unity-lab/screenshots/${STAMP}_ext/" && echo SHOTS_STAGED
echo "SCREENSHOT_DIR=${STAMP}_ext"
echo CAPTURE_COMPLETE
