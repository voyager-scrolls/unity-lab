using System.IO;
using UnityEngine;
using Newtonsoft.Json.Linq;

/// <summary>
/// Data-driven level builder. Reads a JSON layout file and instantiates
/// all props, spawn points, zones, and kill zones in the scene.
/// </summary>
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

        string levelName = layout["name"]?.ToString() ?? "Unnamed Level";
        int version = layout["version"]?.Value<int>() ?? 1;
        Debug.Log("LEVEL_BUILDER: Building '" + levelName + "' v" + version);

        // Create root
        GameObject root = new GameObject("Level_" + levelName.Replace(" ", "_"));

        // Process rooms
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
                        string prefabPath = prop["prefab"]?.ToString();
                        if (string.IsNullOrEmpty(prefabPath)) continue;

                        GameObject prefab = UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                        if (prefab == null)
                        {
                            Debug.LogWarning("LEVEL_BUILDER: Prefab not found: " + prefabPath);
                            continue;
                        }

                        JArray pos = prop["position"] as JArray;
                        Vector3 position = Vector3.zero;
                        if (pos != null && pos.Count >= 3)
                        {
                            position = new Vector3(pos[0].Value<float>(), pos[1].Value<float>(), pos[2].Value<float>());
                        }

                        JArray rot = prop["rotation"] as JArray;
                        Vector3 rotation = Vector3.zero;
                        if (rot != null && rot.Count >= 3)
                        {
                            rotation = new Vector3(rot[0].Value<float>(), rot[1].Value<float>(), rot[2].Value<float>());
                        }

                        JArray scl = prop["scale"] as JArray;
                        Vector3 scale = Vector3.one;
                        if (scl != null && scl.Count >= 3)
                        {
                            scale = new Vector3(scl[0].Value<float>(), scl[1].Value<float>(), scl[2].Value<float>());
                        }

                        GameObject instance = (GameObject)UnityEditor.PrefabUtility.InstantiatePrefab(prefab);
                        instance.transform.position = position;
                        instance.transform.eulerAngles = rotation;
                        instance.transform.localScale = scale;
                        instance.transform.SetParent(roomRoot.transform);

                        string tag = prop["tag"]?.ToString();
                        if (!string.IsNullOrEmpty(tag))
                            instance.tag = tag;
                    }
                }

                // Spawn points
                JArray spawnPoints = room["spawnPoints"] as JArray;
                if (spawnPoints != null)
                {
                    foreach (JObject sp in spawnPoints)
                    {
                        JArray spPos = sp["position"] as JArray;
                        Vector3 spPosition = Vector3.zero;
                        if (spPos != null && spPos.Count >= 3)
                        {
                            spPosition = new Vector3(
                                spPos[0].Value<float>(),
                                spPos[1].Value<float>(),
                                spPos[2].Value<float>());
                        }
                        int team = sp["team"] != null ? sp["team"].Value<int>() : 1;
                        string spType = sp["type"]?.ToString() ?? "delta";

                        GameObject spObj = new GameObject("SpawnPoint_" + spType + "_" + team);
                        spObj.transform.position = spPosition;
                        spObj.transform.SetParent(roomRoot.transform);

                        // Add bl_SpawnPoint component if available
                        var spawnComp = spObj.AddComponent(System.Type.GetType("bl_SpawnPoint"));
                        if (spawnComp != null)
                        {
                            var teamField = spawnComp.GetType().GetField("m_Team");
                            if (teamField != null)
                            {
                                // Team enum: None=0, Team1=1, Team2=2, All=3
                                teamField.SetValue(spawnComp, team);
                            }
                        }
                    }
                }

                // Kill zones
                JArray killZones = room["killZones"] as JArray;
                if (killZones != null)
                {
                    foreach (JObject kz in killZones)
                    {
                        JArray kzPos = kz["position"] as JArray;
                        JArray kzSize = kz["size"] as JArray;
                        Vector3 kzPosition = Vector3.zero;
                        if (kzPos != null && kzPos.Count >= 3) kzPosition = new Vector3(kzPos[0].Value<float>(), kzPos[1].Value<float>(), kzPos[2].Value<float>());
                        Vector3 kzSizeV = new Vector3(10f, 1f, 10f);
                        if (kzSize != null && kzSize.Count >= 3) kzSizeV = new Vector3(kzSize[0].Value<float>(), kzSize[1].Value<float>(), kzSize[2].Value<float>());

                        GameObject kzObj = new GameObject("KillZone");
                        kzObj.transform.position = kzPosition;
                        kzObj.transform.SetParent(roomRoot.transform);
                        BoxCollider bc = kzObj.AddComponent<BoxCollider>();
                        bc.size = kzSizeV;
                        bc.isTrigger = true;
                    }
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
                JArray spPos = sp["position"] as JArray;
                Vector3 spPosition = Vector3.zero;
                if (spPos != null && spPos.Count >= 3)
                {
                    spPosition = new Vector3(
                        spPos[0].Value<float>(),
                        spPos[1].Value<float>(),
                        spPos[2].Value<float>());
                }
                int team = sp["team"] != null ? sp["team"].Value<int>() : 1;

                GameObject spObj = new GameObject("GlobalSpawn_" + team);
                spObj.transform.position = spPosition;
                spObj.transform.SetParent(globalRoot.transform);
            }
        }

        UnityEditor.EditorUtility.SetDirty(root);
        Debug.Log("LEVEL_BUILDER: Level '" + levelName + "' built successfully. Root: " + root.name);
    }
}