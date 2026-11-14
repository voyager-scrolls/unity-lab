#!/bin/bash
# capture_monitor.sh - close-up views of the centre teller workstation from both sides
# to establish which way SM_Prop_Computer_01 faces (screen to teller or to lobby).
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
STAMP=$(date +%s)

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/HeistLevel.unity" || { echo NO_SCENE; exit 6; }
echo PREFLIGHT_OK
command -v xvfb-run >/dev/null 2>&1 && echo XVFB_OK || { echo XVFB_MISSING; exit 6; }

mkdir -p "$PROJ/Assets/Editor" /content/shots3
cat > "$PROJ/Assets/Editor/CaptureMonitor.cs" << 'CSEOF'
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class CaptureMonitor
{
    public static void Capture()
    {
        EditorSceneManager.OpenScene("Assets/MFPS/Scenes/HeistLevel.unity", OpenSceneMode.Single);
        Directory.CreateDirectory("/content/shots3");
        int W = 1280;
        int H = 720;
        var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32);

        var camGo = new GameObject("CaptureCamMon");
        var cam = camGo.AddComponent<Camera>();
        cam.nearClipPlane = 0.05f;
        cam.farClipPlane = 260f;
        cam.targetTexture = rt;

        Vector3[] pos = new Vector3[]
        {
            new Vector3(0f, 1.55f, 7.4f),
            new Vector3(0f, 1.55f, 9.35f),
            new Vector3(1.35f, 1.5f, 7.5f),
            new Vector3(1.35f, 1.5f, 9.2f)
        };
        Vector3[] look = new Vector3[]
        {
            new Vector3(0f, 1.45f, 8.4f),
            new Vector3(0f, 1.45f, 8.4f),
            new Vector3(0f, 1.45f, 8.4f),
            new Vector3(0f, 1.45f, 8.4f)
        };
        float[] fov = new float[] { 32f, 32f, 42f, 42f };

        for (int i = 0; i < pos.Length; i++)
        {
            cam.fieldOfView = fov[i];
            camGo.transform.position = pos[i];
            camGo.transform.LookAt(look[i], Vector3.up);
            RenderAndSave(cam, rt, W, H, "/content/shots3/mon_" + i + ".png");
        }

        Debug.Log("CAPTURE_DONE 4");
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

xvfb-run -a -s "-screen 0 1280x720x24" "$UNITY" -batchmode -quit -projectPath "$PROJ" -executeMethod CaptureMonitor.Capture -logFile /content/capture_mon.log 2>&1 || true
if grep -q "Aborting batchmode" /content/capture_mon.log 2>/dev/null; then
  echo CAPTURE_FAIL
  grep -n "error CS\|Exception\|Aborting" /content/capture_mon.log | head -15
  exit 6
fi
grep -n "CAPTURE_DONE" /content/capture_mon.log | tail -1
SHOTS=$(ls /content/shots3/*.png 2>/dev/null | wc -l)
echo "SHOTS=$SHOTS"
test "$SHOTS" -ge 4 || { echo TOO_FEW_SHOTS; tail -20 /content/capture_mon.log; exit 6; }
mkdir -p "/content/drive/MyDrive/unity-lab/screenshots/${STAMP}_mon"
cp /content/shots3/*.png "/content/drive/MyDrive/unity-lab/screenshots/${STAMP}_mon/" && echo SHOTS_STAGED
echo "SCREENSHOT_DIR=${STAMP}_mon"
echo CAPTURE_COMPLETE
