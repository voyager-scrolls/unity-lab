#!/bin/bash
# capture_bankwall2.sh - cleaner angled views of the teller back-office behind the BANK-sign wall,
# plus one angled lobby view of the sign itself. Stages to Drive screenshots/<stamp>_bankwall2/.
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
STAMP=$(date +%s)

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/HeistLevel.unity" || { echo NO_SCENE; exit 6; }
echo PREFLIGHT_OK

command -v xvfb-run >/dev/null 2>&1 && echo XVFB_OK || { echo XVFB_MISSING; exit 6; }

mkdir -p "$PROJ/Assets/Editor" /content/shots5
cat > "$PROJ/Assets/Editor/CaptureBankWall2.cs" << 'CSEOF'
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class CaptureBankWall2
{
    public static void Capture()
    {
        EditorSceneManager.OpenScene("Assets/MFPS/Scenes/HeistLevel.unity", OpenSceneMode.Single);
        Directory.CreateDirectory("/content/shots5");
        int W = 1280;
        int H = 720;
        var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32);

        var camGo = new GameObject("CaptureCamBankWall2");
        var cam = camGo.AddComponent<Camera>();
        cam.nearClipPlane = 0.08f;
        cam.farClipPlane = 260f;
        cam.targetTexture = rt;

        Vector3[] pos = new Vector3[]
        {
            new Vector3(-8.0f, 1.65f, 12.0f),
            new Vector3(8.0f, 1.65f, 12.0f),
            new Vector3(0f, 1.65f, 14.3f),
            new Vector3(-11.6f, 1.65f, 14.4f),
            new Vector3(5.0f, 1.75f, 5.5f)
        };
        Vector3[] look = new Vector3[]
        {
            new Vector3(-0.5f, 1.9f, 10.2f),
            new Vector3(0.5f, 1.9f, 10.2f),
            new Vector3(0f, 2.0f, 10.0f),
            new Vector3(4.0f, 1.7f, 11.0f),
            new Vector3(0f, 3.1f, 9.9f)
        };
        float[] fov = new float[] { 72f, 72f, 70f, 75f, 48f };

        for (int i = 0; i < pos.Length; i++)
        {
            cam.fieldOfView = fov[i];
            camGo.transform.position = pos[i];
            camGo.transform.LookAt(look[i], Vector3.up);
            RenderAndSave(cam, rt, W, H, "/content/shots5/bw2_" + i + ".png");
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

xvfb-run -a -s "-screen 0 1280x720x24" "$UNITY" -batchmode -quit -projectPath "$PROJ" -executeMethod CaptureBankWall2.Capture -logFile /content/capture_bw2.log 2>&1 || true
if grep -q "Aborting batchmode" /content/capture_bw2.log 2>/dev/null; then
  echo CAPTURE_FAIL
  grep -n "error CS\|Exception\|Aborting" /content/capture_bw2.log | head -15
  exit 6
fi
grep -n "CAPTURE_DONE" /content/capture_bw2.log | tail -1
SHOTS=$(ls /content/shots5/*.png 2>/dev/null | wc -l)
echo "SHOTS=$SHOTS"
test "$SHOTS" -ge 5 || { echo TOO_FEW_SHOTS; tail -20 /content/capture_bw2.log; exit 6; }
mkdir -p "/content/drive/MyDrive/unity-lab/screenshots/${STAMP}_bankwall2"
cp /content/shots5/*.png "/content/drive/MyDrive/unity-lab/screenshots/${STAMP}_bankwall2/" && echo SHOTS_STAGED
echo "SCREENSHOT_DIR=${STAMP}_bankwall2"
echo CAPTURE_COMPLETE
