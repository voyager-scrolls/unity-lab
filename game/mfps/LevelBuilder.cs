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

                        // Position using Value<float>()
                        float px = 0f, py = 0f, pz = 0f;
                        if (prop["position"] is JArray pos && pos.Count >= 3)
                        {
                            px = pos[0].Value<float>(); py = pos[1].Value<float>(); pz = pos[2].Value<float>();
                        }
                        Vector3 position = new Vector3(px, py, pz);

                        // Rotation using Value<float>()
                        float rx = 0f, ry = 0f, rz = 0f;
                        if (prop["rotation"] is JArray rot && rot.Count >= 3)
                        {
                            rx = rot[0].Value<float>(); ry = rot[1].Value<float>(); rz = rot[2].Value<float>();
                        }
                        Vector3 rotation = new Vector3(rx, ry, rz);

                        // Scale using Value<float>()
                        float sx = 1f, sy = 1f, sz = 1f;
                        if (prop["scale"] is JArray scl && scl.Count >= 3)
                        {
                            sx = scl[0].Value<float>(); sy = scl[1].Value<float>(); sz = scl[2].Value<float>();
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
                            spx = spPos[0].Value<float>(); spy = spPos[1].Value<float>(); spz = spPos[2].Value<float>();
                        }
                        int team = 1;
                        if (sp["team"] != null) team = sp["team"].Value<int>();

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
                            kzx = kzPos[0].Value<float>(); kzy = kzPos[1].Value<float>(); kzz = kzPos[2].Value<float>();
                        }
                        float kzSx = 10f, kzSy = 1f, kzSz = 10f;
                        if (kz["size"] is JArray kzSzArr && kzSzArr.Count >= 3)
                        {
                            kzSx = kzSzArr[0].Value<float>(); kzSy = kzSzArr[1].Value<float>(); kzSz = kzSzArr[2].Value<float>();
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