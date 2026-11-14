#!/bin/bash
# inspect_teller.sh - dump renderers in the teller back-office and around the vault-door wall.
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/HeistLevel.unity" || { echo NO_SCENE; exit 6; }
echo PREFLIGHT_OK

cat > "$PROJ/Assets/Editor/InspectTeller.cs" << 'CSEOF'
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class InspectTeller
{
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/MFPS/Scenes/HeistLevel.unity", OpenSceneMode.Single);
        var sb = new StringBuilder();
        var rends = Object.FindObjectsOfType<MeshRenderer>(true);
        sb.AppendLine("RENDERERS=" + rends.Length);
        sb.AppendLine("== TELLER ROOM (z 9.2..16.2, |x|<=13) ==");
        foreach (var r in rends)
        {
            Bounds b = r.bounds;
            bool inT = b.max.z > 9.2f && b.min.z < 16.2f && b.max.x > -13f && b.min.x < 13f;
            if (!inT) continue;
            sb.AppendLine(string.Format("{0} | pos=({1:F2},{2:F2},{3:F2}) size=({4:F2},{5:F2},{6:F2}) centre=({7:F2},{8:F2},{9:F2}) mat={10}",
                r.name,
                r.transform.position.x, r.transform.position.y, r.transform.position.z,
                b.size.x, b.size.y, b.size.z,
                b.center.x, b.center.y, b.center.z,
                r.sharedMaterial != null ? r.sharedMaterial.name : "null"));
        }
        sb.AppendLine("== VAULT DOOR WALL BAND (z 14.2..15.8) ==");
        foreach (var r in rends)
        {
            Bounds b = r.bounds;
            bool inW = b.min.z < 15.8f && b.max.z > 14.2f;
            if (!inW) continue;
            sb.AppendLine(string.Format("{0} | pos=({1:F2},{2:F2},{3:F2}) size=({4:F2},{5:F2},{6:F2}) minz={7:F2} maxz={8:F2} minx={9:F2} maxx={10:F2} mat={11}",
                r.name,
                r.transform.position.x, r.transform.position.y, r.transform.position.z,
                b.size.x, b.size.y, b.size.z,
                b.min.z, b.max.z, b.min.x, b.max.x,
                r.sharedMaterial != null ? r.sharedMaterial.name : "null"));
        }
        File.WriteAllText("/content/inspect_teller.txt", sb.ToString());
        Debug.Log("INSPECT_TELLER_DONE");
    }
}
CSEOF
echo SCRIPT_WRITTEN

rm -rf "$PROJ/Temp"
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod InspectTeller.Run -logFile /content/inspect_teller.log 2>&1 || true
grep -q "INSPECT_TELLER_DONE" /content/inspect_teller.log && echo DUMPED || { echo INSPECT_FAIL; tail -15 /content/inspect_teller.log; exit 6; }
cp /content/inspect_teller.txt /content/drive/MyDrive/unity-lab/specs/inspect_teller.txt && echo DUMP_STAGED
wc -l /content/inspect_teller.txt
echo INSPECT_COMPLETE
