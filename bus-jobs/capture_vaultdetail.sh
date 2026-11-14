#!/bin/bash
# capture_vaultdetail.sh - close views of the hijacked-vault dressing (charge, gear, cases).
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
STAMP=$(date +%s)

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/HeistLevel.unity" || { echo NO_SCENE; exit 6; }
echo PREFLIGHT_OK

command -v xvfb-run >/dev/null 2>&1 && echo XVFB_OK || { echo XVFB_MISSING; exit 6; }

mkdir -p "$PROJ/Assets/Editor" /content/shots6
cat > "$PROJ/Assets/Editor/CaptureVaultDetail.cs" << 'CSEOF'
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class CaptureVaultDetail
{
    public static void Capture()
    {
        EditorSceneManager.OpenScene("Assets/MFPS/Scenes/HeistLevel.unity", OpenSceneMode.Single);
        Directory.CreateDirectory("/content/shots6");
        int W = 1280;
        int H = 720;
        var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32);

        var camGo = new GameObject("CaptureCamVault");
        var cam = camGo.AddComponent<Camera>();
        cam.nearClipPlane = 0.08f;
        cam.farClipPlane = 260f;
        cam.targetTexture = rt;

        Vector3[] pos = new Vector3[]
        {
            new Vector3(0.6f, 1.7f, 18.2f),
            new Vector3(1.2f, 1.7f, 19.0f),
            new Vector3(-2.0f, 1.7f, 15.8f),
            new Vector3(-1.0f, 1.7f, 21.8f)
        };
        Vector3[] look = new Vector3[]
        {
            new Vector3(-5.0f, 0.5f, 19.6f),
            new Vector3(5.4f, 0.5f, 19.2f),
            new Vector3(-0.5f, 0.6f, 17.6f),
            new Vector3(-4.6f, 0.5f, 19.4f)
        };
        float[] fov = new float[] { 68f, 68f, 72f, 62f };

        for (int i = 0; i < pos.Length; i++)
        {
            cam.fieldOfView = fov[i];
            camGo.transform.position = pos[i];
            camGo.transform.LookAt(look[i], Vector3.up);
            RenderAndSave(cam, rt, W, H, "/content/shots6/vd_" + i + ".png");
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

xvfb-run -a -s "-screen 0 1280x720x24" "$UNITY" -batchmode -quit -projectPath "$PROJ" -executeMethod CaptureVaultDetail.Capture -logFile /content/capture_vd.log 2>&1 || true
if grep -q "Aborting batchmode" /content/capture_vd.log 2>/dev/null; then
  echo CAPTURE_FAIL
  grep -n "error CS\|Exception\|Aborting" /content/capture_vd.log | head -15
  exit 6
fi
grep -n "CAPTURE_DONE" /content/capture_vd.log | tail -1
SHOTS=$(ls /content/shots6/*.png 2>/dev/null | wc -l)
echo "SHOTS=$SHOTS"
test "$SHOTS" -ge 4 || { echo TOO_FEW_SHOTS; tail -20 /content/capture_vd.log; exit 6; }
mkdir -p "/content/drive/MyDrive/unity-lab/screenshots/${STAMP}_vault"
cp /content/shots6/*.png "/content/drive/MyDrive/unity-lab/screenshots/${STAMP}_vault/" && echo SHOTS_STAGED
echo "SCREENSHOT_DIR=${STAMP}_vault"
echo CAPTURE_COMPLETE
