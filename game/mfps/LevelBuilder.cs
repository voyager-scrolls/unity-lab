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
            Debug.LogError("LEVEL_BUILDER: No layout file at " + jsonPath);
            return;
        }
        string json = File.ReadAllText(jsonPath);
        JObject layout = JObject.Parse(json);
        string levelName = layout["name"]?.ToString() ?? "Unnamed";
        int version = layout["version"]?.Value<int>() ?? 1;
        Debug.Log("LEVEL_BUILDER: Building '" + levelName + "' v" + version);

        // Extract layout data upfront (avoids compile issues with inline ?.Value patterns)
        JArray rooms = layout["rooms"] as JArray;
        float[] roomMinX = new float[rooms.Count];
        float[] roomMinY = new float[rooms.Count];
        float[] roomMinZ = new float[rooms.Count];
        float[] roomMaxX = new float[rooms.Count];
        float[] roomMaxY = new float[rooms.Count];
        float[] roomMaxZ = new float[rooms.Count];
        for (int r = 0; r < rooms.Count; r++)
        {
            JObject room = rooms[r] as JObject;
            JArray bounds = room["bounds"] as JArray;
            if (bounds != null && bounds.Count >= 6)
            {
                roomMinX[r] = (float)bounds[0];
                roomMinY[r] = (float)bounds[1];
                roomMinZ[r] = (float)bounds[2];
                roomMaxX[r] = (float)bounds[3];
                roomMaxY[r] = (float)bounds[4];
                roomMaxZ[r] = (float)bounds[5];
            }
        }

        GameObject root = new GameObject("Level_" + levelName.Replace(" ", "_"));

        // Process rooms
        for (int r = 0; r < rooms.Count; r++)
        {
            JObject room = rooms[r] as JObject;
            string roomId = room["id"]?.ToString() ?? "room";
            GameObject roomRoot = new GameObject("Room_" + roomId);
            roomRoot.transform.SetParent(root.transform);

            // Props
            JArray props = room["props"] as JArray;
            if (props != null)
            {
                foreach (JObject prop in props)
                {
                    string prefabPath = prop["prefab"]?.ToString();
                    if (string.IsNullOrEmpty(prefabPath)) continue;
                    GameObject prefab = UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                    if (prefab == null) { Debug.LogWarning("LEVEL_BUILDER: Prefab not found: " + prefabPath); continue; }

                    // Position (safe extraction)
                    float px = 0f, py = 0f, pz = 0f;
                    if (prop["position"] is JArray pos && pos.Count >= 3)
                    {
                        px = pos[0].Value<float>(); py = pos[1].Value<float>(); pz = pos[2].Value<float>();
                    }
                    Vector3 position = new Vector3(px, py, pz);

                    // Rotation
                    float rx = 0f, ry = 0f, rz = 0f;
                    if (prop["rotation"] is JArray rot && rot.Count >= 3)
                    {
                        rx = rot[0].Value<float>(); ry = rot[1].Value<float>(); rz = rot[2].Value<float>();
                    }
                    Vector3 rotation = new Vector3(rx, ry, rz);

                    // Scale
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

                    string tag = prop["tag"]?.ToString();
                    if (!string.IsNullOrEmpty(tag)) instance.tag = tag;
                }
            }

            // Spawn points
            JArray spawnPoints = room["spawnPoints"] as JArray;
            if (spawnPoints != null)
            {
                foreach (JObject sp in spawnPoints)
                {
                    float spx = 0f, spy = 1f, spz = 2f;
                    if (sp["position"] is JArray spPos && spPos.Count >= 3)
                    {
                        spx = spPos[0].Value<float>(); spy = spPos[1].Value<float>(); spz = spPos[2].Value<float>();
                    }
                    int team = sp["team"] != null ? sp["team"].Value<int>() : 1;
                    string spType = sp["type"]?.ToString() ?? "delta";

                    GameObject spObj = new GameObject("SpawnPoint_" + spType + "_" + team);
                    spObj.transform.position = new Vector3(spx, spy, spz);
                    spObj.transform.SetParent(roomRoot.transform);

                    var spawnComp = spObj.AddComponent(System.Type.GetType("bl_SpawnPoint"));
                    if (spawnComp != null)
                    {
                        var teamField = spawnComp.GetType().GetField("m_Team");
                        if (teamField != null) teamField.SetValue(spawnComp, team);
                    }
                }
            }

            // Kill zones
            JArray killZones = room["killZones"] as JArray;
            if (killZones != null)
            {
                foreach (JObject kz in killZones)
                {
                    float kzx = 0f, kzy = 1f, kzz = 10f;
                    if (kz["position"] is JArray kzPos && kzPos.Count >= 3)
                    {
                        kzx = kzPos[0].Value<float>(); kzy = kzPos[1].Value<float>(); kzz = kzPos[2].Value<float>();
                    }
                    float kzSx = 10f, kzSy = 1f, kzSz = 10f;
                    if (kz["size"] is JArray kzSize && kzSize.Count >= 3)
                    {
                        kzSx = kzSize[0].Value<float>(); kzSy = kzSize[1].Value<float>(); kzSz = kzSize[2].Value<float>();
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

        // Global spawn points
        JArray globalSpawns = layout["globalSpawnPoints"] as JArray;
        if (globalSpawns != null)
        {
            GameObject globalRoot = new GameObject("GlobalSpawnPoints");
            globalRoot.transform.SetParent(root.transform);
            foreach (JObject sp in globalSpawns)
            {
                float spx = 0f, spy = 1f, spz = 2f;
                if (sp["position"] is JArray spPos && spPos.Count >= 3)
                {
                    spx = spPos[0].Value<float>(); spy = spPos[1].Value<float>(); spz = spPos[2].Value<float>();
                }
                int team = sp["team"] != null ? sp["team"].Value<int>() : 1;

                GameObject spObj = new GameObject("GlobalSpawn_" + team);
                spObj.transform.position = new Vector3(spx, spy, spz);
                spObj.transform.SetParent(globalRoot.transform);
            }
        }

        UnityEditor.EditorUtility.SetDirty(root);
        Debug.Log("LEVEL_BUILDER: Level '" + levelName + "' built successfully. Root: " + root.name);
    }
}