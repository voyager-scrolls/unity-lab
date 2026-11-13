#!/bin/bash
# prefab_anatomy.sh - dump child hierarchy + bounds + colliders for key kit prefabs.
set -e
MFPSROOT=/content/drive/MyDrive/unity-lab
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR_BIN; exit 6; }
test -d "$PROJ/Assets/PolygonHeist" || { echo NO_HEIST; exit 6; }
echo PREFLIGHT_OK

mkdir -p "$PROJ/Assets/Editor"
cat > "$PROJ/Assets/Editor/PrefabAnatomy.cs" << 'CSEOF'
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

public static class PrefabAnatomy
{
    static readonly string[] Folders = { "Assets/PolygonHeist/Prefab/Props", "Assets/PolygonHeist/Prefab/Environment" };
    static readonly string[] Names = {
        "SM_Prop_TellerDesk_01", "SM_Prop_TellerDesk_02", "SM_Prop_TellerDesk_03",
        "SM_Prop_TellerDesk_Barrier_01", "SM_Prop_Camera_01", "SM_Prop_Computer_01",
        "SM_Prop_Computer_Screen_01", "SM_Prop_Computer_Keyboard_01", "SM_Prop_Computer_Mouse_01",
        "SM_Prop_DisplayCase_01", "SM_Prop_DisplayCase_02", "SM_Prop_SafeDepositBoxes_01",
        "SM_Prop_VaultTrolley_01", "SM_Prop_Desk_01", "SM_Prop_Desk_02", "SM_Prop_Seat_01",
        "SM_Prop_Table_01", "SM_Prop_Sign_Bank_01", "SM_Prop_Aircon_01", "SM_Prop_AirVent_01",
        "SM_Env_Wall_Interior_Door_01", "SM_Env_Wall_Exterior_DoubleDoor_01", "SM_Env_Wall_Exterior_Window_01"
    };

    public static void Dump()
    {
        StringBuilder sb = new StringBuilder();
        sb.Append("[\n");
        int written = 0;
        foreach (string name in Names)
        {
            string path = FindPath(name);
            if (path == null)
            {
                if (written > 0) sb.Append(",\n");
                sb.Append("{\"name\":\"").Append(name).Append("\",\"missing\":true}");
                written++;
                continue;
            }
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null) continue;
            if (written > 0) sb.Append(",\n");
            sb.Append("{\"name\":\"").Append(name).Append("\",\"path\":\"").Append(path).Append("\",");
            Renderer[] renderers = prefab.GetComponentsInChildren<Renderer>(true);
            Collider[] colliders = prefab.GetComponentsInChildren<Collider>(true);
            int tris = 0;
            foreach (MeshFilter mf in prefab.GetComponentsInChildren<MeshFilter>(true))
                if (mf.sharedMesh != null) tris += mf.sharedMesh.triangles.Length / 3;
            sb.Append("\"renderers\":").Append(renderers.Length);
            sb.Append(",\"colliders\":").Append(colliders.Length);
            sb.Append(",\"triangles\":").Append(tris);
            sb.Append(",\"children\":[");
            Transform[] all = prefab.GetComponentsInChildren<Transform>(true);
            bool first = true;
            foreach (Transform t in all)
            {
                if (!first) sb.Append(",");
                first = false;
                Renderer r = t.GetComponent<Renderer>();
                string b = "none";
                if (r != null)
                {
                    Bounds bb = r.bounds;
                    b = F(bb.min.x) + "," + F(bb.min.y) + "," + F(bb.min.z) + ".." +
                        F(bb.max.x) + "," + F(bb.max.y) + "," + F(bb.max.z);
                }
                sb.Append("{\"name\":\"").Append(Esc(t.name)).Append("\",");
                sb.Append("\"lp\":[").Append(F(t.localPosition.x)).Append(",").Append(F(t.localPosition.y)).Append(",").Append(F(t.localPosition.z)).Append("],");
                sb.Append("\"ls\":[").Append(F(t.localScale.x)).Append(",").Append(F(t.localScale.y)).Append(",").Append(F(t.localScale.z)).Append("],");
                sb.Append("\"collider\":").Append(t.GetComponent<Collider>() != null ? "true" : "false").Append(",");
                sb.Append("\"bounds\":\"").Append(Esc(b)).Append("\"}");
            }
            sb.Append("]}");
            written++;
        }
        sb.Append("\n]\n");
        File.WriteAllText("/content/prefab_anatomy.json", sb.ToString());
        Debug.Log("ANATOMY_DONE count=" + written);
    }

    static string FindPath(string name)
    {
        foreach (string folder in Folders)
        {
            string p = folder + "/" + name + ".prefab";
            if (File.Exists(p)) return p;
        }
        string[] guids = AssetDatabase.FindAssets(name + " t:Prefab");
        foreach (string g in guids)
        {
            string p = AssetDatabase.GUIDToAssetPath(g);
            if (p.EndsWith("/" + name + ".prefab")) return p;
        }
        return null;
    }

    static string F(float v) { return v.ToString("0.###", CultureInfo.InvariantCulture); }

    static string Esc(string s)
    {
        string bslash = ((char)92).ToString();
        string dquote = ((char)34).ToString();
        return s.Replace(bslash, "/").Replace(dquote, "'");
    }
}
CSEOF
echo ANATOMY_WRITTEN

rm -rf "$PROJ/Temp"
mkdir -p /tmp/xdg; chmod 700 /tmp/xdg
export XDG_RUNTIME_DIR=/tmp/xdg

"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod PrefabAnatomy.Dump -logFile /content/anatomy.log 2>&1 || true
if grep -q "Aborting batchmode" /content/anatomy.log 2>/dev/null; then
  echo ANATOMY_FAIL
  grep -n "error CS\|Exception" /content/anatomy.log | head -20
  exit 6
fi
grep -n "ANATOMY_DONE" /content/anatomy.log | tail -1
test -f /content/prefab_anatomy.json || { echo NO_ANATOMY; exit 6; }
wc -c /content/prefab_anatomy.json
mkdir -p "$MFPSROOT/specs"
cp /content/prefab_anatomy.json "$MFPSROOT/specs/prefab-anatomy.json" && echo ANATOMY_STAGED
echo ANATOMY_COMPLETE
