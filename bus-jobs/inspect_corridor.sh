#!/bin/bash
# inspect_corridor.sh - dump every renderer inside corridorL so unknown objects can be identified.
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/HeistLevel.unity" || { echo NO_SCENE; exit 6; }
echo PREFLIGHT_OK

cat > "$PROJ/Assets/Editor/InspectCorridor.cs" << 'CSEOF'
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class InspectCorridor
{
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/MFPS/Scenes/HeistLevel.unity", OpenSceneMode.Single);
        var sb = new StringBuilder();
        var rends = Object.FindObjectsOfType<MeshRenderer>(true);
        sb.AppendLine("RENDERERS=" + rends.Length);
        foreach (var r in rends)
        {
            Bounds b = r.bounds;
            bool inL = b.max.x > -13.2f && b.min.x < -7.0f && b.max.z > 14.5f && b.min.z < 25.5f;
            if (!inL) continue;
            Vector3 s = b.size;
            if (s.x < 0.001f || s.z < 0.001f) continue;
            sb.AppendLine(string.Format("{0} | pos=({1:F2},{2:F2},{3:F2}) size=({4:F2},{5:F2},{6:F2}) centre=({7:F2},{8:F2},{9:F2}) mat={10}",
                r.name,
                r.transform.position.x, r.transform.position.y, r.transform.position.z,
                s.x, s.y, s.z,
                b.center.x, b.center.y, b.center.z,
                r.sharedMaterial != null ? r.sharedMaterial.name : "null"));
        }
        File.WriteAllText("/content/inspect_corridor.txt", sb.ToString());
        Debug.Log("INSPECT_CORRIDOR_DONE");
    }
}
CSEOF
echo SCRIPT_WRITTEN

rm -rf "$PROJ/Temp"
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod InspectCorridor.Run -logFile /content/inspect_corridor.log 2>&1 || true
grep -q "INSPECT_CORRIDOR_DONE" /content/inspect_corridor.log && echo DUMPED || { echo INSPECT_FAIL; tail -15 /content/inspect_corridor.log; exit 6; }
cp /content/inspect_corridor.txt /content/drive/MyDrive/unity-lab/specs/inspect_corridor.txt && echo DUMP_STAGED
wc -l /content/inspect_corridor.txt
echo INSPECT_COMPLETE
