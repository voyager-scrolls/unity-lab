#!/bin/bash
# capture_interior.sh - interior-only review shoot for the bank map
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
STAMP=$(date +%s)

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/HeistLevel.unity" || { echo NO_SCENE; exit 6; }
echo PREFLIGHT_OK

if ! command -v xvfb-run >/dev/null 2>&1; then
  (apt-get update -qq && apt-get install -y -qq xvfb libgl1-mesa-dri) >/dev/null 2>&1 || true
fi
echo XVFB_OK

mkdir -p /content/shots_int
rm -f /content/shots_int/*.png

cat > "$PROJ/Assets/Editor/CaptureInterior.cs" << 'CSEOF'
using System.IO;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public static class CaptureInterior
{
    public static void Capture()
    {
        EditorSceneManager.OpenScene("Assets/MFPS/Scenes/HeistLevel.unity");
        int W = 1280, H = 720;
        RenderTexture rt = new RenderTexture(W, H, 24);
        GameObject go = new GameObject("CapCam");
        Camera cam = go.AddComponent<Camera>();
        cam.targetTexture = rt;
        cam.nearClipPlane = 0.05f;
        cam.farClipPlane = 120f;

        // 00 lobby wide / 01 lobby-left / 02 lobby-right / 03 left passage from lobby
        // 04 left passage from teller / 05 corridorL length / 06 corridorL vault wall
        // 07 vault door context / 08 vault door close / 09 vault interior / 10 vault right side
        // 11 right passage from lobby / 12 corridorR length / 13 lobby ceiling / 14 lobby portrait wall
        // 15 entrance clock / 16 queue ropes left / 17 teller left cage / 18 teller right cage
        // 19 vault counting table / 20 corridorL manager desk / 21 corridorR watch desk
        // 22 vault left deposit wall / 23 lobby mirror wall / 24 queue ropes right
        float[][] pos = new float[][] {
            new float[]{0f,1.7f,1.0f}, new float[]{-11f,1.8f,3f}, new float[]{11f,1.8f,3f},
            new float[]{-10f,1.7f,5.5f}, new float[]{-8.5f,1.7f,12.3f}, new float[]{-10.8f,1.7f,15.2f},
            new float[]{-10.5f,1.7f,19.2f}, new float[]{0f,1.7f,11.3f}, new float[]{0f,1.7f,13.5f},
            new float[]{0f,1.7f,18.4f}, new float[]{0f,1.7f,17.5f}, new float[]{10f,1.7f,5.5f},
            new float[]{10.6f,1.7f,18.8f}, new float[]{0f,1.7f,2.5f}, new float[]{0f,1.7f,5.5f},
            new float[]{0f,1.7f,4.5f}, new float[]{-9.0f,1.7f,4.6f}, new float[]{-8.0f,1.7f,10.7f},
            new float[]{8.0f,1.7f,10.7f}, new float[]{0f,1.7f,16.2f}, new float[]{-11.6f,1.9f,15.6f},
            new float[]{11.6f,1.9f,15.6f}, new float[]{-3.5f,1.7f,16.2f}, new float[]{0f,1.7f,5.5f},
            new float[]{9.0f,1.7f,4.6f}
        };
        float[][] look = new float[][] {
            new float[]{0f,2.2f,10.5f}, new float[]{4f,1.2f,9f}, new float[]{-4f,1.2f,9f},
            new float[]{-10f,1.4f,12f}, new float[]{-10.5f,1.3f,7f}, new float[]{-10.8f,1.2f,19.5f},
            new float[]{-7.5f,1.2f,15.2f}, new float[]{0f,1.5f,15f}, new float[]{0f,1.5f,15f},
            new float[]{0f,1.4f,15f}, new float[]{7.5f,1.4f,19f}, new float[]{10f,1.4f,12f},
            new float[]{10.6f,1.2f,15f}, new float[]{0f,5.9f,8.5f}, new float[]{-12.2f,2.4f,5.5f},
            new float[]{0f,3.9f,0.1f}, new float[]{0f,0.9f,6.8f}, new float[]{-10.3f,1.1f,12.2f},
            new float[]{10.3f,1.1f,12.2f}, new float[]{0f,1.1f,19.4f}, new float[]{-9.8f,1.0f,17.2f},
            new float[]{9.8f,1.0f,17.2f}, new float[]{-6.5f,1.4f,18.6f}, new float[]{12.2f,2.4f,5.5f},
            new float[]{0f,0.9f,6.8f}
        };
        float[] fov = new float[] {70f,65f,65f,65f,65f,65f,65f,60f,55f,65f,65f,65f,65f,75f,65f,
                                   60f,70f,60f,60f,65f,65f,65f,65f,65f,70f};

        Texture2D tex = new Texture2D(W, H, TextureFormat.RGB24, false);
        for (int i = 0; i < pos.Length; i++)
        {
            cam.fieldOfView = fov[i];
            cam.transform.position = new Vector3(pos[i][0], pos[i][1], pos[i][2]);
            cam.transform.LookAt(new Vector3(look[i][0], look[i][1], look[i][2]));
            cam.Render();
            RenderTexture.active = rt;
            tex.ReadPixels(new Rect(0, 0, W, H), 0, 0);
            tex.Apply();
            File.WriteAllBytes(string.Format("/content/shots_int/int_{0:00}.png", i), tex.EncodeToPNG());
        }
        RenderTexture.active = null;
        Debug.Log("CAPTURE_DONE " + pos.Length);
    }
}
CSEOF

echo CAPTURE_SCRIPT_WRITTEN
xvfb-run -a -s "-screen 0 1280x720x24" "$UNITY" -batchmode -quit -projectPath "$PROJ" \
  -executeMethod CaptureInterior.Capture -logFile /content/capture_int.log || true

SHOTS=$(ls /content/shots_int/*.png 2>/dev/null | wc -l)
echo SHOTS=$SHOTS
[ "$SHOTS" -ge 25 ] || { echo TOO_FEW_SHOTS; tail -20 /content/capture_int.log; exit 6; }

mkdir -p /content/drive/MyDrive/unity-lab/screenshots/${STAMP}_int
cp /content/shots_int/*.png /content/drive/MyDrive/unity-lab/screenshots/${STAMP}_int/
echo SHOTS_STAGED
echo SCREENSHOT_DIR=${STAMP}_int
echo CAPTURE_COMPLETE
