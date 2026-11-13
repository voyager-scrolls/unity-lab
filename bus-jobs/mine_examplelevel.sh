#!/bin/bash
# mine_examplelevel.sh - dump MFPS ExampleLevel.unity (the known-good map): every GameObject with
# transform + component types + collider/renderer bounds + lights + build settings + RenderSettings.
set -e
MFPSROOT=/content/drive/MyDrive/unity-lab
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR_BIN; exit 6; }
test -d "$PROJ/Assets/MFPS" || { echo NO_PROJECT; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/ExampleLevel.unity" || { echo NO_EXAMPLE_SCENE; exit 6; }
echo PREFLIGHT_OK

mkdir -p "$PROJ/Assets/Editor"
cat > "$PROJ/Assets/Editor/ExampleMiner.cs" << 'CSEOF'
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

public static class ExampleMiner
{
    public static void Mine()
    {
        EditorSceneManager.OpenScene("Assets/MFPS/Scenes/ExampleLevel.unity", OpenSceneMode.Single);

        StringBuilder sb = new StringBuilder();
        sb.Append("{\n\"scene\":\"ExampleLevel\",\n");
        sb.Append("\"ambient\":{\"mode\":\"").Append(RenderSettings.ambientMode).Append("\",");
        sb.Append("\"light\":[").Append(F(RenderSettings.ambientLight.r)).Append(",").Append(F(RenderSettings.ambientLight.g)).Append(",").Append(F(RenderSettings.ambientLight.b)).Append("],");
        sb.Append("\"fog\":").Append(RenderSettings.fog ? "true" : "false").Append(",");
        sb.Append("\"skybox\":\"").Append(RenderSettings.skybox != null ? Esc(RenderSettings.skybox.name) : "none").Append("\"},\n");
        sb.Append("\"buildScenes\":[");
        EditorBuildSettingsScene[] bs = EditorBuildSettings.scenes;
        for (int i = 0; i < bs.Length; i++)
        {
            if (i > 0) sb.Append(",");
            sb.Append("\"").Append(Esc(bs[i].path)).Append("\"");
        }
        sb.Append("],\n");

        sb.Append("\"objects\":[\n");
        GameObject[] gos = Object.FindObjectsByType<GameObject>(FindObjectsSortMode.None);
        int count = 0;
        foreach (GameObject go in gos)
        {
            if (go == null) continue;
            StringBuilder comps = new StringBuilder();
            Component[] cs = go.GetComponents<Component>();
            bool first = true;
            foreach (Component c in cs)
            {
                if (c == null) continue;
                if (!first) comps.Append("|");
                comps.Append(c.GetType().Name);
                first = false;
            }
            string col = "none";
            Collider cc = go.GetComponent<Collider>();
            if (cc != null)
            {
                Bounds cb = cc.bounds;
                col = cc.GetType().Name + "@" + F(cb.min.x) + "," + F(cb.min.y) + "," + F(cb.min.z) + ".." +
                      F(cb.max.x) + "," + F(cb.max.y) + "," + F(cb.max.z);
            }
            string ren = "none";
            Renderer rr = go.GetComponent<Renderer>();
            if (rr != null)
            {
                Bounds rb = rr.bounds;
                ren = F(rb.min.x) + "," + F(rb.min.y) + "," + F(rb.min.z) + ".." +
                      F(rb.max.x) + "," + F(rb.max.y) + "," + F(rb.max.z);
            }
            string light = "";
            Light li = go.GetComponent<Light>();
            if (li != null)
                light = "\"light\":{\"type\":\"" + li.type + "\",\"intensity\":" + F(li.intensity) +
                        ",\"shadows\":\"" + li.shadows + "\",\"range\":" + F(li.range) + ",\"color\":[" +
                        F(li.color.r) + "," + F(li.color.g) + "," + F(li.color.b) + "]},";

            if (count > 0) sb.Append(",\n");
            Vector3 p = go.transform.position;
            Vector3 e = go.transform.eulerAngles;
            Vector3 s = go.transform.localScale;
            sb.Append("{\"path\":\"").Append(Esc(PathOf(go.transform))).Append("\",");
            sb.Append("\"active\":").Append(go.activeInHierarchy ? "true" : "false").Append(",");
            sb.Append("\"pos\":[").Append(F(p.x)).Append(",").Append(F(p.y)).Append(",").Append(F(p.z)).Append("],");
            sb.Append("\"rot\":[").Append(F(e.x)).Append(",").Append(F(e.y)).Append(",").Append(F(e.z)).Append("],");
            sb.Append("\"scale\":[").Append(F(s.x)).Append(",").Append(F(s.y)).Append(",").Append(F(s.z)).Append("],");
            sb.Append(light);
            sb.Append("\"components\":\"").Append(Esc(comps.ToString())).Append("\",");
            sb.Append("\"collider\":\"").Append(Esc(col)).Append("\",");
            sb.Append("\"renderer\":\"").Append(Esc(ren)).Append("\"}");
            count++;
        }
        sb.Append("\n],\n\"count\":").Append(count).Append("\n}\n");
        File.WriteAllText("/content/examplelevel.json", sb.ToString());
        Debug.Log("EXAMPLE_MINED count=" + count);
    }

    static string F(float v) { return v.ToString("0.###", CultureInfo.InvariantCulture); }

    static string Esc(string s)
    {
        string bslash = ((char)92).ToString();
        string dquote = ((char)34).ToString();
        return s.Replace(bslash, "/").Replace(dquote, "'");
    }

    static string PathOf(Transform t)
    {
        string p = t.name;
        Transform cur = t.parent;
        int depth = 0;
        while (cur != null && depth < 10) { p = cur.name + "/" + p; cur = cur.parent; depth++; }
        return p;
    }
}
CSEOF
echo MINER_WRITTEN

rm -rf "$PROJ/Temp"
mkdir -p /tmp/xdg; chmod 700 /tmp/xdg
export XDG_RUNTIME_DIR=/tmp/xdg

"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod ExampleMiner.Mine -logFile /content/example_mine.log 2>&1 || true
if grep -q "Aborting batchmode" /content/example_mine.log 2>/dev/null; then
  echo MINE_FAIL
  grep -n "error CS\|Exception" /content/example_mine.log | head -20
  exit 6
fi
grep -n "EXAMPLE_MINED" /content/example_mine.log | tail -1
test -f /content/examplelevel.json || { echo NO_DUMP; exit 6; }
wc -c /content/examplelevel.json
mkdir -p "$MFPSROOT/specs"
cp /content/examplelevel.json "$MFPSROOT/specs/examplelevel.json" && echo DUMP_STAGED
echo MINE_COMPLETE
