#!/bin/bash
# inspect_roof.sh - ceiling coverage raycasts, camera anchors, and a SWAT bone dump for posing.
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/HeistLevel.unity" || { echo NO_SCENE; exit 6; }
echo PREFLIGHT_OK

cat > "$PROJ/Assets/Editor/InspectRoof.cs" << 'CSEOF'
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class InspectRoof
{
    static string Grid(string room, float x0, float x1, float z0, float z1)
    {
        var sb = new StringBuilder();
        int holes = 0;
        int total = 0;
        var lines = new StringBuilder();
        for (float x = x0 + 0.25f; x < x1; x += 0.5f)
        {
            for (float z = z0 + 0.25f; z < z1; z += 0.5f)
            {
                total++;
                RaycastHit hit;
                bool got = Physics.Raycast(new Vector3(x, 1.0f, z), Vector3.up, out hit, 8f);
                float y = got ? hit.point.y : -1f;
                if (!got || y > 3.6f)
                {
                    holes++;
                    lines.AppendLine(string.Format("  HOLE {0} x={1:F2} z={2:F2} hit={3:F2} {4}", room, x, z, y, got ? hit.collider.name : "none"));
                }
            }
        }
        sb.AppendLine(string.Format("{0}: cells={1} holes={2}", room, total, holes));
        sb.Append(lines);
        return sb.ToString();
    }

    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/MFPS/Scenes/HeistLevel.unity", OpenSceneMode.Single);
        Physics.SyncTransforms();
        var sb = new StringBuilder();
        sb.AppendLine("== CEILING COVERAGE (ray up from y=1, hole = first hit above 3.6m) ==");
        sb.Append(Grid("vault", -7.5f, 7.5f, 15f, 25f));
        sb.Append(Grid("corridorL", -12.5f, -7.5f, 15f, 25f));
        sb.Append(Grid("corridorR", 7.5f, 12.5f, 15f, 25f));
        sb.Append(Grid("teller", -12.5f, 12.5f, 10f, 15f));

        sb.AppendLine("== CAMERAS ==");
        foreach (var r in Object.FindObjectsOfType<MeshRenderer>(true))
        {
            if (!r.name.Contains("Camera")) continue;
            Bounds b = r.bounds;
            sb.AppendLine(string.Format("{0} pos=({1:F2},{2:F2},{3:F2}) miny={4:F2} maxy={5:F2} size=({6:F2},{7:F2},{8:F2})",
                r.name, r.transform.position.x, r.transform.position.y, r.transform.position.z,
                b.min.y, b.max.y, b.size.x, b.size.y, b.size.z));
        }

        sb.AppendLine("== SWAT PREFAB BONES ==");
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/PolygonHeist/Prefab/Characters/Character_Male_SWAT_01.prefab");
        if (prefab == null)
        {
            var guids = AssetDatabase.FindAssets("Character_Male_SWAT_01 t:Prefab");
            if (guids.Length > 0)
                prefab = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(guids[0]));
        }
        if (prefab == null)
        {
            sb.AppendLine("SWAT PREFAB NOT FOUND");
        }
        else
        {
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            var anim = inst.GetComponentInChildren<Animator>();
            if (anim != null)
            {
                if (anim.avatar != null && anim.avatar.isValid)
                {
                    sb.AppendLine("bones humanoid=" + anim.isHuman);
                }
                else
                {
                    sb.AppendLine("avatar invalid");
                }
            }
            foreach (var t in inst.GetComponentsInChildren<Transform>(true))
            {
                sb.AppendLine(string.Format("  BONE {0} parent={1} lp=({2:F2},{3:F2},{4:F2})",
                    t.name, t.parent != null ? t.parent.name : "-",
                    t.localPosition.x, t.localPosition.y, t.localPosition.z));
            }
            Object.DestroyImmediate(inst);
        }
        File.WriteAllText("/content/inspect_roof.txt", sb.ToString());
        Debug.Log("INSPECT_ROOF_DONE");
    }
}
CSEOF
echo SCRIPT_WRITTEN

rm -rf "$PROJ/Temp"
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod InspectRoof.Run -logFile /content/inspect_roof.log 2>&1 || true
grep -q "INSPECT_ROOF_DONE" /content/inspect_roof.log && echo DUMPED || { echo INSPECT_FAIL; tail -20 /content/inspect_roof.log; exit 6; }
cp /content/inspect_roof.txt /content/drive/MyDrive/unity-lab/specs/inspect_roof.txt && echo DUMP_STAGED
wc -l /content/inspect_roof.txt
echo INSPECT_COMPLETE
