#!/bin/bash
# heist-catalog-build.sh — generate prefab catalog JSON from POLYGON Heist Pack
# Requires: MFPS project on VM (creates if missing), Heist pack on Drive
set -e

MFPSROOT=/content/drive/MyDrive/unity-lab
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
PKG=$MFPSROOT/templates/mfps-2.0-v1.75/mfps-2.0-v1.7.5.unitypackage
PUN2ZIP=$MFPSROOT/templates/mfps-2.0-v1.75/pun2-v2.16-mirror3.zip
HEISTPKG=$MFPSROOT/assets/polygon-heist-v1.5/POLYGON-Heist-Pack-v1.5.unitypackage
MATHPKG=$MFPSROOT/assets/math-library-v1.3.5/MathLibrary-v1.3.5.unitypackage
ULF=$MFPSROOT/secrets/Unity_lic.ulf
UNITY_BIN=/content/unity_bin.txt

echo "=== PREFLIGHT ==="
test -f "$UNITY_BIN" || { echo NO_UNITY_BIN; exit 6; }
test -x "$UNITY" || { echo NO_EDITOR_BIN; exit 6; }
test -f "$PKG" || { echo NO_MFPS_PKG; exit 6; }
test -f "$HEISTPKG" || { echo NO_HEIST_PKG; exit 6; }
echo PREFLIGHT_OK

echo "=== LICENCE ==="
if [ ! -f ~/.local/share/unity3d/Unity/Unity_lic.ulf ]; then
  mkdir -p ~/.local/share/unity3d/Unity
  cp "$ULF" ~/.local/share/unity3d/Unity/Unity_lic.ulf && echo ULF_INSTALLED || { echo ULF_COPY_FAIL; exit 6; }
else
  echo ULF_PRESENT
fi

echo "=== ENSURE WINDOWS MODULE ==="
PEMB=/content/ue/Editor/Data/PlaybackEngines
if [ ! -d "$PEMB/WindowsStandaloneSupport" ]; then
  echo "WIN_MODULE_MISSING — extracting from Drive cache"
  TARB=$MFPSROOT/cache/Windows.pkg
  if [ ! -s "$TARB" ]; then echo NO_WINDOWS_PKG; exit 6; fi
  rm -rf /tmp/pkgm1 /tmp/pkgm2
  mkdir -p /tmp/pkgm1 /tmp/pkgm2
  7z x "$TARB" -o/tmp/pkgm1 >/dev/null 2>&1
  PAYLOAD=$(find /tmp/pkgm1 -name 'Payload*' | head -1)
  7z x "$PAYLOAD" -o/tmp/pkgm2 >/dev/null 2>&1
  INNER=$(find /tmp/pkgm2 -type d -name 'WindowsStandaloneSupport' | head -1)
  if [ -z "$INNER" ]; then INNER=$(find /tmp/pkgm2 -type d | grep -i windows | head -1); fi
  cp -a "$INNER" "$PEMB/" && echo WIN_MODULE_INSTALLED || { echo WIN_MODULE_FAIL; exit 6; }
else
  echo WIN_MODULE_PRESENT
fi

echo "=== CREATE PROJECT (if missing) ==="
if [ ! -d "$PROJ/Assets" ]; then
  rm -rf "$PROJ"
  mkdir -p "$PROJ"
  "$UNITY" -batchmode -nographics -quit -createProject "$PROJ" -logFile /content/mfps_create.log 2>&1 || true
  echo "CREATE_PROJECT_FRESH"
else
  echo "PROJECT_EXISTS"
fi

echo "=== WRITE UNITY6 MANIFEST (ugui + postprocessing + modules, BEFORE editor opens project) ==="
python3 - "$PROJ" <<'PYEOF'
import json, os, sys
proj = sys.argv[1]
manifest_path = os.path.join(proj, "Packages", "manifest.json")
os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
manifest = {
  "dependencies": {
    "com.unity.ugui": "2.0.0",
    "com.unity.postprocessing": "3.2.2",
    "com.unity.modules.ai": "1.0.0",
    "com.unity.modules.animation": "1.0.0",
    "com.unity.modules.audio": "1.0.0",
    "com.unity.modules.particlesystem": "1.0.0",
    "com.unity.modules.terrain": "1.0.0",
    "com.unity.modules.ui": "1.0.0",
    "com.unity.modules.uielements": "1.0.0",
    "com.unity.modules.unitywebrequest": "1.0.0",
    "com.unity.modules.video": "1.0.0",
    "com.unity.modules.wind": "1.0.0",
    "com.unity.modules.physics": "1.0.0",
    "com.unity.modules.physics2d": "1.0.0"
  }
}
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)
print("MANIFEST_WRITTEN")
PYEOF

echo "=== INSTALL PUN2 (folder copy with metas) ==="
if [ ! -d "$PROJ/Assets/Photon" ]; then
  rm -rf /content/pun2x
  mkdir -p /content/pun2x
  unzip -q -o "$PUN2ZIP" -d /content/pun2x || { echo PUN2_UNZIP_FAIL; exit 6; }
  mkdir -p "$PROJ/Assets/Photon"
  cp -a /content/pun2x/. "$PROJ/Assets/Photon/" || { echo PUN2_COPY_FAIL; exit 6; }
  echo "PUN2_INSTALLED"
else
  echo "PUN2_ALREADY_PRESENT"
fi
PUN2_CS=$(find "$PROJ/Assets/Photon" -name "*.cs" | wc -l)
echo "PUN2_CS=$PUN2_CS"

echo "=== IMPORT MFPS CORE (tolerant) ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -importPackage "$PKG" -logFile /content/mfps_import.log 2>&1 || true
MFPS_DIR_OK=0
if [ -d "$PROJ/Assets/MFPS" ]; then MFPS_DIR_OK=1; echo "MFPS_DIR_OK"; else echo "MFPS_DIR_MISSING"; fi
MFPS_CS=$(find "$PROJ/Assets/MFPS" -name "*.cs" 2>/dev/null | wc -l)
echo "MFPS_CS=$MFPS_CS"

echo "=== IMPORT HEIST PACK (tolerant) ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -importPackage "$HEISTPKG" -logFile /content/heist_import.log 2>&1 || true
HEIST_DIR_OK=0
if [ -d "$PROJ/Assets/PolygonHeist" ]; then HEIST_DIR_OK=1; echo "HEIST_DIR_OK"; else echo "HEIST_DIR_MISSING"; exit 6; fi
HEIST_PREFAB_COUNT=$(find "$PROJ/Assets/PolygonHeist/Prefab" -name "*.prefab" | wc -l)
echo "HEIST_PREFABS=$HEIST_PREFAB_COUNT"

echo "=== IMPORT MATH LIBRARY (tolerant) ==="
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -importPackage "$MATHPKG" -logFile /content/math_import.log 2>&1 || true
MATH_DIR_OK=0
if [ -d "$PROJ/Assets/MathLibrary" ] || [ -d "$PROJ/Assets/Math Library" ] || [ -d "$PROJ/Assets/MathLibraryForUnity" ]; then MATH_DIR_OK=1; echo "MATH_DIR_OK"; else echo "MATH_DIR_NOT_FOUND (checking all dirs)"; find "$PROJ/Assets" -maxdepth 1 -type d | head -20; fi

echo "=== MANIFEST REWRITE (after imports) ==="
python3 - "$PROJ" <<'PYEOF'
import json, os, sys
proj = sys.argv[1]
manifest_path = os.path.join(proj, "Packages", "manifest.json")
manifest = {
  "dependencies": {
    "com.unity.ugui": "2.0.0",
    "com.unity.postprocessing": "3.2.2",
    "com.unity.modules.ai": "1.0.0",
    "com.unity.modules.animation": "1.0.0",
    "com.unity.modules.audio": "1.0.0",
    "com.unity.modules.particlesystem": "1.0.0",
    "com.unity.modules.terrain": "1.0.0",
    "com.unity.modules.ui": "1.0.0",
    "com.unity.modules.uielements": "1.0.0",
    "com.unity.modules.unitywebrequest": "1.0.0",
    "com.unity.modules.video": "1.0.0",
    "com.unity.modules.wind": "1.0.0",
    "com.unity.modules.physics": "1.0.0",
    "com.unity.modules.physics2d": "1.0.0"
  }
}
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)
print("MANIFEST_REWRITTEN")
PYEOF
rm -f "$PROJ/Packages/packages-lock.json"

echo "=== WRITE CATALOG BUILDER SCRIPT ==="
mkdir -p "$PROJ/Assets/Editor"
cp /content/drive/MyDrive/unity-lab/templates/mfps-2.0-v1.75/HeistCatalogBuilder.cs "$PROJ/Assets/Editor/HeistCatalogBuilder.cs" 2>/dev/null || {
  # Fallback: write from heredoc
  cat > "$PROJ/Assets/Editor/HeistCatalogBuilder.cs" << 'CSEOF'
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

public static class HeistCatalogBuilder
{
    public static void Build()
    {
        string[] prefabGuids = AssetDatabase.FindAssets("t:Prefab", new[] { "Assets/PolygonHeist/Prefab" });
        StringBuilder sb = new StringBuilder();
        sb.Append("[\n");

        int count = 0;
        foreach (string guid in prefabGuids)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null) continue;

            if (count > 0) sb.Append(",\n");

            Renderer[] renderers = prefab.GetComponentsInChildren<Renderer>(true);
            Bounds bounds = new Bounds(Vector3.zero, Vector3.zero);
            bool hasBounds = false;
            foreach (Renderer r in renderers)
            {
                if (!hasBounds) { bounds = r.bounds; hasBounds = true; }
                else bounds.Encapsulate(r.bounds);
            }

            Collider[] colliders = prefab.GetComponentsInChildren<Collider>(true);
            string colliderType = "none";
            string colliderSize = "null";
            if (colliders.Length > 0)
            {
                Collider c = colliders[0];
                if (c is BoxCollider) { colliderType = "Box"; colliderSize = ((BoxCollider)c).size.ToString(); }
                else if (c is SphereCollider) { colliderType = "Sphere"; colliderSize = ((SphereCollider)c).radius.ToString(); }
                else if (c is CapsuleCollider) { colliderType = "Capsule"; colliderSize = ((CapsuleCollider)c).height.ToString(); }
                else if (c is MeshCollider) { colliderType = "Mesh"; colliderSize = "mesh"; }
                else colliderType = c.GetType().Name;
            }

            string materialName = "none";
            if (renderers.Length > 0 && renderers[0].sharedMaterial != null)
                materialName = renderers[0].sharedMaterial.name;

            int triangles = 0;
            MeshFilter[] meshFilters = prefab.GetComponentsInChildren<MeshFilter>(true);
            foreach (MeshFilter mf in meshFilters)
            {
                if (mf.sharedMesh != null) triangles += mf.sharedMesh.triangles.Length / 3;
            }

            string category = "Unknown";
            string[] parts = path.Split('/');
            if (parts.Length >= 4) category = parts[3];

            string tags = prefab.tag;
            if (tags == "Untagged") tags = "";

            sb.Append("  {\n");
            sb.Append("    \"name\": \"" + prefab.name.Replace("\"", "\\\"") + "\",\n");
            sb.Append("    \"path\": \"" + path + "\",\n");
            sb.Append("    \"guid\": \"" + guid + "\",\n");
            sb.Append("    \"category\": \"" + category + "\",\n");
            sb.Append("    \"bounds\": { \"min\": [" + bounds.min.x + ", " + bounds.min.y + ", " + bounds.min.z + "], \"max\": [" + bounds.max.x + ", " + bounds.max.y + ", " + bounds.max.z + "] },\n");
            sb.Append("    \"collider\": { \"type\": \"" + colliderType + "\", \"size\": \"" + colliderSize + "\" },\n");
            sb.Append("    \"material\": \"" + materialName + "\",\n");
            sb.Append("    \"triangles\": " + triangles + ",\n");
            sb.Append("    \"tags\": \"" + tags + "\"\n");
            sb.Append("  }");

            count++;
        }

        sb.Append("\n]\n");

        string outPath = "/content/heist-catalog.json";
        File.WriteAllText(outPath, sb.ToString());
        Debug.Log("HEIST_CATALOG_BUILT count=" + count + " path=" + outPath);
    }
}
CSEOF
  echo "CATALOG_SCRIPT_WRITTEN_FALLBACK"
}
echo "CATALOG_SCRIPT_READY"

echo "=== COMPILE GATE ==="
rm -rf "$PROJ/Temp"
mkdir -p /tmp/xdg; chmod 700 /tmp/xdg
export XDG_RUNTIME_DIR=/tmp/xdg
printf 'pcm.!default { type null }\nctl.!default { type null }\n' > /etc/asound.conf
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod HeistCatalogBuilder.Build -logFile /content/catalog_compile.log 2>&1
COMPILE_RC=$?
echo "COMPILE_RC=$COMPILE_RC"
CS_ERRORS=$(grep -c "error CS" /content/catalog_compile.log 2>/dev/null || echo 0)
echo "CS_ERRORS=$CS_ERRORS"
if [ "$CS_ERRORS" != "0" ]; then
  echo "COMPILE_GATE_FAIL"
  grep -n "error CS" /content/catalog_compile.log | head -20
  exit 6
fi
echo "COMPILE_GATE_OK"

echo "=== VERIFY CATALOG ==="
if [ -f /content/heist-catalog.json ]; then
  CATALOG_SIZE=$(wc -c < /content/heist-catalog.json)
  CATALOG_COUNT=$(python3 -c "import json; print(len(json.load(open('/content/heist-catalog.json'))))")
  echo "CATALOG_SIZE=$CATALOG_SIZE"
  echo "CATALOG_ENTRIES=$CATALOG_COUNT"
else
  echo "CATALOG_FILE_MISSING"
  exit 6
fi

echo "=== STAGE CATALOG TO DRIVE ==="
cp /content/heist-catalog.json "$MFPSROOT/catalogs/heist-catalog.json" && echo "CATALOG_STAGED_OK" || { echo "CATALOG_STAGE_FAIL"; exit 6; }

echo "=== HEIST_CATALOG_COMPLETE ==="
