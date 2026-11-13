using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

public static class HeistCatalogBuilder
{
    [MenuItem("Tools/Build Heist Catalog")]
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

            // Bounds from renderers
            Renderer[] renderers = prefab.GetComponentsInChildren<Renderer>(true);
            Bounds bounds = new Bounds(Vector3.zero, Vector3.zero);
            bool hasBounds = false;
            foreach (Renderer r in renderers)
            {
                if (!hasBounds) { bounds = r.bounds; hasBounds = true; }
                else bounds.Encapsulate(r.bounds);
            }

            // Collider info
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

            // Material name
            string materialName = "none";
            if (renderers.Length > 0 && renderers[0].sharedMaterial != null)
                materialName = renderers[0].sharedMaterial.name;

            // Triangle count
            int triangles = 0;
            MeshFilter[] meshFilters = prefab.GetComponentsInChildren<MeshFilter>(true);
            foreach (MeshFilter mf in meshFilters)
            {
                if (mf.sharedMesh != null) triangles += mf.sharedMesh.triangles.Length / 3;
            }

            // Category from path
            string category = "Unknown";
            string[] parts = path.Split('/');
            if (parts.Length >= 4) category = parts[3]; // Assets/PolygonHeist/Prefab/<Category>

            // Tags
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
