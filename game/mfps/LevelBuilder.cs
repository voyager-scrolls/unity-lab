using System.IO;
using UnityEngine;
using Newtonsoft.Json.Linq;

public static class LevelBuilder
{
    [MenuItem("Tools/Build Level from JSON")]
    public static void BuildFromJson()
    {
        string jsonPath = "/content/level-layout.json";
        if (!File.Exists(jsonPath))
        {
            Debug.LogError("LEVEL_BUILDER: No layout file");
            return;
        }
        string json = File.ReadAllText(jsonPath);
        JObject layout = JObject.Parse(json);
        string levelName = layout["name"]?.ToString() ?? "Unnamed";
        int version = layout["version"]?.Value<int>() ?? 1;
        Debug.Log("Building level '" + levelName + "' v" + version);

        GameObject root = new GameObject("LevelRoot");
        JArray rooms = layout["rooms"] as JArray;
        if (rooms != null)
        {
            foreach (JObject room in rooms)
            {
                string roomId = room["id"]?.ToString() ?? "room";
                GameObject roomRoot = new GameObject("Room_" + roomId);
                roomRoot.transform.SetParent(root.transform);

                // Props
                JArray props = room["props"] as JArray;
                if (props != null)
                {
                    foreach (JObject prop in props)
                    {
                        string pf = prop["prefab"]?.ToString();
                        if (string.IsNullOrEmpty(pf)) continue;
                        GameObject prefab = UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(pf);
                        if (prefab == null) { Debug.LogWarning("Prefab not found: " + pf); continue; }

                        // Position
                        float px = 0f, py = 0f, pz = 0f;
                        if (prop["position"] is JArray pos && pos.Count >= 3)
                        {
                            px = (float)pos[0]; py = (float)pos[1]; pz = (float)pos[2];
                        }
                        Vector3 position = new Vector3(px, py, pz);

                        // Rotation
 float rx = 0f, ry = 0f, rz = 0f;
                        if (prop["rotation"] is JArray rot && rot.Count >= 3)
                        {
                            rx = (float)rot[0]; ry = (float)rot[1]; rz = (float)rot[2];
                        }
                        Vector3 rotation = new Vector3(rx, ry, rz);

                        // Scale
                        float sx = 1f, sy = 1f, sz = 1f;
                        if (prop["scale"] is JArray scl && scl.Count >= 3)
                        {
                            sx = (float)scl[0]; sy = (float)scl[1]; sz = (float)scl[2];
                        }
                        Vector3 scale = new Vector3(sx, sy, sz);

                        GameObject instance = (GameObject)UnityEditor.PrefabUtility.InstantiatePrefab(prefab);
                        instance.transform.position = position;
                        instance.transform.eulerAngles = rotation;
                        instance.transform.localScale = scale;
                        instance.transform.SetParent(roomRoot.transform);
                    }
                }

                // Spawn points
                JArray spawns = room["spawnPoints"] as JArray;
                if (spawns != null)
                {
                    foreach (JObject sp in spawns)
                    {
                        float spx = 0f, spy = 1f, spz = 2f;
                        if (sp["position"] is JArray spPos && spPos.Count >= 3)
                        {
                            spx = (float)spPos[0]; spy = (float)spPos[1]; spz = (float)spPos[2];
                        }
                        int team = 1;
                        if (sp["team"] != null) team = (int)sp["team"];

                        GameObject spObj = new GameObject("Spawn_T" + team);
                        spObj.transform.position = new Vector3(spx, spy, spz);
                        spObj.transform.SetParent(roomRoot.transform);
                    }
                }

                // Kill zones
                JArray kzs = room["killZones"] as JArray;
                if (kzs != null)
                {
                    foreach (JObject kz in kzs)
                    {
                        float kzx = 0f, kzy = 1f, kzz = 10f;
                        if (kz["position"] is JArray kzPos && kzPos.Count >= 3)
                        {
                            kzx = (float)kzPos[0]; kzy = (float)kzPos[1]; kzz = (float)kzPos[2];
                        }
                        float kzSx = 10f, kzSy = 1f, kzSz = 10f;
                        if (kz["size"] is JArray kzSzArr && kzSzArr.Count >= 3)
                        {
                            kzSx = (float)kzSzArr[0]; kzSy = (float)kzSzArr[1]; kzSz = (float)kzSzArr[2];
                        }

                        GameObject kzObj = new GameObject("KillZone");
                        kzObj.transform.position = new Vector3(kzx, kzy, kzz);
                        kzObj.transform.SetParent(roomRoot.transform);
                        BoxCollider bc = kzObj.AddComponent<BoxCollider>();
                        bc.size = new Vector3(kzSx, kzSy, kzSz);
                        bc.isTrigger = true;
                    }
                }
            }
        }

        UnityEditor.EditorUtility.SetDirty(root);
        Debug.Log("Level built: " + root.name);
    }
}