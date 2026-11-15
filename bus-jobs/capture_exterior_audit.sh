#!/bin/bash
# capture_exterior_audit.sh - targeted exterior audit for the bank shell
# front elevation, sign/top-window row, pilasters, side and back walls, roof edge.
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
STAMP=$(date +%s)

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/HeistLevel.unity" || { echo NO_SCENE; exit 6; }
echo PREFLIGHT_OK

if ! command -v xvfb-run >/dev/null 2>&1; then
  apt-get update -qq && apt-get install -y -qq xvfb libgl1-mesa-dri >/dev/null 2>&1 || true
fi
command -v xvfb-run >/dev/null 2>&1 || { echo NO_XVFB; exit 6; }
echo XVFB_OK

mkdir -p /content/shots_extaudit
rm -f /content/shots_extaudit/*.png

mkdir -p "$PROJ/Assets/Editor"
cat > "$PROJ/Assets/Editor/CaptureExteriorAudit.cs" << 'CSEOF'
using System.IO;
using UnityEngine;
using UnityEditor;
using UnityEngine.SceneManagement;
using UnityEditor.SceneManagement;

public static class CaptureExteriorAudit
{
    public static void Capture()
    {
        EditorSceneManager.OpenScene("Assets/MFPS/Scenes/HeistLevel.unity");
        int W = 1280, H = 720;
        RenderTexture rt = new RenderTexture(W, H, 24);
        GameObject go = new GameObject("AuditCam");
        Camera cam = go.AddComponent<Camera>();
        cam.targetTexture = rt;
        cam.nearClipPlane = 0.05f;
        cam.farClipPlane = 400f;

        // 00 front wide / 01 front mid / 02-03 front obliques / 04 front top
        // 05 sign / 06-07 top window row / 08-09 pilaster tops / 10 entrance
        // 11 portico underside / 12-13 facade mids / 14-15 side walls high
        // 16-17 side walls 3/4 / 18-19 back wall / 20-21 high 3/4 corners
        // 22 roof edge / 23 orthographic topdown
        float[][] pos = new float[][] {
            new float[]{0f,6.0f,-30f},   new float[]{0f,6.5f,-22f},
            new float[]{-20f,8f,-18f},   new float[]{20f,8f,-18f},
            new float[]{0f,14f,-14f},    new float[]{0f,9.5f,-10f},
            new float[]{-7f,10.5f,-10f}, new float[]{7f,10.5f,-10f},
            new float[]{-11f,10f,-8f},   new float[]{11f,10f,-8f},
            new float[]{0f,1.7f,-7f},    new float[]{0f,1.8f,-5.5f},
            new float[]{-9f,5f,-9f},     new float[]{9f,5f,-9f},
            new float[]{-22f,16f,10f},   new float[]{22f,16f,10f},
            new float[]{-22f,14f,-12f},  new float[]{22f,14f,-12f},
            new float[]{0f,16f,35f},     new float[]{0f,20f,30f},
            new float[]{-26f,18f,-26f},  new float[]{26f,18f,-26f},
            new float[]{0f,18f,-18f},    new float[]{0f,90f,-2f}
        };
        float[][] look = new float[][] {
            new float[]{0f,6f,0f},       new float[]{0f,6.5f,0f},
            new float[]{0f,7f,0f},       new float[]{0f,7f,0f},
            new float[]{0f,12f,0f},      new float[]{0f,9.5f,0f},
            new float[]{-7f,10.5f,0f},   new float[]{7f,10.5f,0f},
            new float[]{-11f,10f,0f},    new float[]{11f,10f,0f},
            new float[]{0f,2.0f,4f},     new float[]{0f,6f,0f},
            new float[]{-9f,6f,0f},      new float[]{9f,6f,0f},
            new float[]{-12.5f,8f,10f},  new float[]{12.5f,8f,10f},
            new float[]{-10f,7f,10f},    new float[]{10f,7f,10f},
            new float[]{0f,8f,20f},      new float[]{0f,10f,20f},
            new float[]{0f,8f,6f},       new float[]{0f,8f,6f},
            new float[]{0f,12f,0f},      new float[]{0f,0f,0f}
        };
        float[] fov = new float[] {50f,55f,55f,55f,55f,30f,40f,40f,35f,35f,
                                   60f,70f,45f,45f,50f,50f,55f,55f,55f,50f,
                                   55f,55f,55f,60f};

        Texture2D tex = new Texture2D(W, H, TextureFormat.RGB24, false);
        for (int i = 0; i < 23; i++)
        {
            cam.orthographic = false;
            cam.fieldOfView = fov[i];
            cam.transform.position = new Vector3(pos[i][0], pos[i][1], pos[i][2]);
            cam.transform.LookAt(new Vector3(look[i][0], look[i][1], look[i][2]));
            cam.Render();
            RenderTexture.active = rt;
            tex.ReadPixels(new Rect(0, 0, W, H), 0, 0);
            tex.Apply();
            File.WriteAllBytes(string.Format("/content/shots_extaudit/ea_{0:00}.png", i), tex.EncodeToPNG());
        }

        cam.orthographic = true;
        cam.orthographicSize = 45f;
        cam.transform.position = new Vector3(0f, 90f, -2f);
        cam.transform.rotation = Quaternion.Euler(90f, 0f, 0f);
        cam.Render();
        RenderTexture.active = rt;
        tex.ReadPixels(new Rect(0, 0, W, H), 0, 0);
        tex.Apply();
        File.WriteAllBytes("/content/shots_extaudit/ea_topdown.png", tex.EncodeToPNG());

        RenderTexture.active = null;
        Debug.Log("CAPTURE_DONE " + pos.Length);
    }
}
CSEOF

echo CAPTURE_SCRIPT_WRITTEN
xvfb-run -a -s "-screen 0 1280x720x24" "$UNITY" -batchmode -quit -projectPath "$PROJ" \
  -executeMethod CaptureExteriorAudit.Capture -logFile /content/capture_extaudit.log || true

grep -q "CAPTURE_DONE" /content/capture_extaudit.log || { echo CAPTURE_FAILED; tail -25 /content/capture_extaudit.log; exit 6; }
echo CAPTURE_LOG_OK

SHOTS=$(ls /content/shots_extaudit/*.png 2>/dev/null | wc -l)
echo SHOTS=$SHOTS
[ "$SHOTS" -ge 24 ] || { echo TOO_FEW_SHOTS; tail -20 /content/capture_extaudit.log; exit 6; }

mkdir -p /content/drive/MyDrive/unity-lab/screenshots/${STAMP}_extaudit
cp /content/shots_extaudit/*.png /content/drive/MyDrive/unity-lab/screenshots/${STAMP}_extaudit/
echo SHOTS_STAGED
echo SCREENSHOT_DIR=${STAMP}_extaudit
echo CAPTURE_COMPLETE
