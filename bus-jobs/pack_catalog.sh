#!/bin/bash
# pack_catalog.sh - import the new POLYGON packs and dump a prefab catalogue.
# Output: Drive specs/city-catalog.json (path, category, bounds, collider, material, triangles)
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
DRIVE=/content/drive/MyDrive/unity-lab

echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -d "$PROJ/Assets" || { echo NO_PROJECT; exit 6; }
rm -f "$PROJ/Assets/Editor/CatalogDump.cs"
echo PREFLIGHT_OK

echo "=== PULL PACKS ==="
rm -rf /content/packs
mkdir -p /content/packs
for n in city town battleroyale; do
  cp "/content/drive/MyDrive/unity-lab/assets/packs/pack_$n.unitypackage" /content/packs/ || true
done
PACKS=$(ls /content/packs/pack_*.unitypackage 2>/dev/null | wc -l)
echo "PACKS=$PACKS"
if [ "$PACKS" -lt 3 ]; then echo PULL_FAIL; ls -la /content/packs; exit 6; fi
ls -1 /content/packs/pack_*.unitypackage
echo PACKS_PULLED

echo "=== IMPORT PACKS ==="
for f in /content/packs/pack_*.unitypackage; do
  b=$(basename "$f")
  echo "IMPORT $b"
  "$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -importPackage "$f" -logFile "/content/imp_$b.log" 2>&1 || true
  grep -n "Error opening default X display\|Failed to import package\|Error while importing" "/content/imp_$b.log" 2>/dev/null | tail -3
done
echo "=== ASSET ROOTS ==="
ls -1 "$PROJ/Assets"

echo "=== WRITE DUMPER ==="
mkdir -p "$PROJ/Assets/Editor"
cat > "$PROJ/Assets/Editor/CatalogDump.cs" << 'CSEOF'
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

public static class CatalogDump
{
    static string F(float v) { return v.ToString("0.###", CultureInfo.InvariantCulture); }

    [MenuItem("Tools/Dump Pack Catalog")]
    public static void Run()
    {
        string[] allDirs = Directory.GetDirectories("Assets");
        List<string> roots = new List<string>();
        foreach (string d in allDirs)
        {
            string dn = Path.GetFileName(d);
            string dl = dn.ToLowerInvariant();
            if (dl.Contains("polygon") && !dl.Contains("scifi") && !dl.Contains("sci-fi"))
            {
                roots.Add(d.Replace("\\", "/"));
            }
        }
        if (roots.Count == 0) { Debug.LogError("NO_POLYGON_ROOTS"); return; }
        StringBuilder sb = new StringBuilder();
        sb.Append("{\"entries\":[");
        bool first = true;
        int count = 0;

        foreach (string root in roots)
        {
            if (!AssetDatabase.IsValidFolder(root))
            {
                Debug.LogWarning("MISSING_ROOT " + root);
                continue;
            }
            string[] guids = AssetDatabase.FindAssets("t:Prefab", new string[] { root });
            Debug.Log("ROOT " + root + " prefabs=" + guids.Length);
            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                GameObject go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (go == null) continue;
                Renderer[] rends = go.GetComponentsInChildren<Renderer>(true);
                if (rends.Length == 0) continue;

                Bounds b = rends[0].bounds;
                int tris = 0;
                string mat = "none";
                bool firstMat = true;
                for (int i = 0; i < rends.Length; i++)
                {
                    if (i > 0) b.Encapsulate(rends[i].bounds);
                    Mesh m = null;
                    MeshFilter mf = rends[i].GetComponent<MeshFilter>();
                    if (mf != null) m = mf.sharedMesh;
                    if (m == null)
                    {
                        SkinnedMeshRenderer smr = rends[i] as SkinnedMeshRenderer;
                        if (smr != null) m = smr.sharedMesh;
                    }
                    if (m != null) tris += m.triangles.Length / 3;
                    if (firstMat && rends[i].sharedMaterial != null)
                    {
                        mat = rends[i].sharedMaterial.name;
                        firstMat = false;
                    }
                }

                Collider col = go.GetComponentInChildren<Collider>(true);
                string ct = "none";
                if (col is BoxCollider) ct = "Box";
                else if (col is MeshCollider) ct = "Mesh";
                else if (col is CapsuleCollider) ct = "Capsule";
                else if (col is SphereCollider) ct = "Sphere";

                string lower = path.ToLowerInvariant();
                string cat = "Props";
                if (lower.Contains("/building") || lower.Contains("/house") || lower.Contains("/building")) cat = "Building";
                else if (lower.Contains("/environment") || lower.Contains("/props/env")) cat = "Environment";
                else if (lower.Contains("/vehicle")) cat = "Vehicle";
                else if (lower.Contains("/character")) cat = "Character";
                else if (lower.Contains("/weapon")) cat = "Weapon";
                else if (lower.Contains("/prop")) cat = "Props";
                else if (lower.Contains("/nature") || lower.Contains("/tree")) cat = "Nature";

                if (!first) sb.Append(",");
                first = false;
                count++;

                Vector3 mn = b.min;
                Vector3 mx = b.max;
                sb.Append("{\"name\":\"").Append(go.name)
                  .Append("\",\"path\":\"").Append(path.Replace("\\", "/"))
                  .Append("\",\"category\":\"").Append(cat)
                  .Append("\",\"material\":\"").Append(mat)
                  .Append("\",\"collider\":{\"type\":\"").Append(ct).Append("\"}")
                  .Append(",\"triangles\":").Append(tris)
                  .Append(",\"bounds\":{\"min\":[").Append(F(mn.x)).Append(",").Append(F(mn.y)).Append(",").Append(F(mn.z))
                  .Append("],\"max\":[").Append(F(mx.x)).Append(",").Append(F(mx.y)).Append(",").Append(F(mx.z))
                  .Append("]}}");
            }
        }
        sb.Append("]}");
        File.WriteAllText("/content/city-catalog.json", sb.ToString());
        Debug.Log("CATALOG_DONE entries=" + count);
    }
}
CSEOF
echo DUMPER_WRITTEN

echo "=== DUMP CATALOG ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod CatalogDump.Run -logFile /content/catalog_dump.log 2>&1 || true
grep -n "CATALOG_DONE\|error CS\|MISSING_ROOT\|ROOT " /content/catalog_dump.log | tail -12
test -f /content/city-catalog.json || { echo NO_CATALOG; tail -20 /content/catalog_dump.log; exit 6; }
wc -c /content/city-catalog.json

echo "=== STAGE ==="
cp /content/city-catalog.json /content/drive/MyDrive/unity-lab/specs/city-catalog.json && echo CATALOG_STAGED
echo PACK_CATALOG_COMPLETE
