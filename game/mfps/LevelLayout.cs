using System.IO;
using UnityEngine;

// LevelLayout holds pre-parsed level data from JSON. Generated once and saved as Asset.
[CreateAssetMenu(fileName = "LevelLayout", menu = "Tools/Level Layout")]
public class LevelLayout : ScriptableObject
{
    public string levelName;
    public int version;
    public LevelRoom[] rooms;
    public GlobalSpawnData globalSpawns;
    public string layoutJsonPath; // original JSON for reference
}

[System.Serializable]
public class LevelRoom
{
    public string roomId;
    public string roomName;
    public Bounds bounds; // min/max Vector3
    public LevelProp[] props;
    public LevelSpawnPoint[] spawnPoints;
    public LevelKillZone[] killZones;
}

[System.Serializable]
public class LevelProp
{
    public string prefabPath;
    public Vector3 position;
    public Vector3 rotation;
    public Vector3 scale;
    public string tag;
}

[System.Serializable]
public class LevelSpawnPoint
{
    public Vector3 position;
    public int team;
    public string type; // delta, recon, generic
}

[System.Serializable]
public class LevelKillZone
{
    public Vector3 position;
    public Vector3 size; // extents for BoxCollider
    public bool isTrigger = true;
}

[System.Serializable]
public class GlobalSpawnData
{
    public LevelSpawnPoint[] spawnPoints;
}

// Auto-generate LevelLayout Asset from the JSON layout file
public static class LevelLayoutGenerator
{
    [MenuItem("Tools/Generate Level Layout Asset")]
    public static void Generate()
    {
        string jsonPath = "/content/level-layout.json";
        if (!File.Exists(jsonPath))
        {
            Debug.LogError("LEVEL_LAYOUT: No layout file at " + jsonPath);
            return;
        }

        string json = File.ReadAllText(jsonPath);
        JObject layout = JObject.Parse(json);
        
        LevelLayout asset = ScriptableObject.CreateInstance<LevelLayout>();
        asset.levelName = layout["name"]?.ToString() ?? "Unnamed";
        asset.version = layout["version"]?.Value<int>() ?? 1;
        asset.layoutJsonPath = jsonPath;

        // Parse rooms
        JArray rooms = layout["rooms"] as JArray;
        if (rooms != null)
        {
            asset.rooms = new LevelRoom[rooms.Count];
            for (int r = 0; r < rooms.Count; r++)
            {
                JObject room = rooms[r] as JObject;
                asset.rooms[r].roomId = room["id"]?.ToString() ?? "room";
                asset.rooms[r].roomName = room["name"]?.ToString() ?? roomId;

                // Bounds
                JArray bounds = room["bounds"] as JArray;
                if (bounds != null && bounds.Count >= 6)
                {
                    asset.rooms[r].bounds = new Bounds(
                        new Vector3((float)bounds[0], (float)bounds[1], (float)bounds[2]),
                        new Vector3((float)bounds[3] - (float)bounds[0], (float)bounds[4] - (float)bounds[1], (float)bounds[5] - (float)bounds[2])
                    );
                }

                // Props
                JArray props = room["props"] as JArray;
                if (props != null)
                {
                    asset.rooms[r].props = new LevelProp[props.Count];
                    for (int p = 0; p < props.Count; p++)
                    {
                        JObject prop = props[p] as JObject;
                        asset.rooms[r].props[p].prefabPath = prop["prefab"]?.ToString() ?? "";
                        
                        // Position
                        float px = 0f, py = 0f, pz = 0f;
                        if (prop["position"] is JArray pos && pos.Count >= 3)
                        {
                            px = (float)pos[0]; py = (float)pos[1]; pz = (float)pos[2];
                        }
                        asset.rooms[r].props[p].position = new Vector3(px, py, pz);

                        // Rotation
                        float rx = 0f, ry = 0f, rz = 0f;
                        if (prop["rotation"] is JArray rot && rot.Count >= 3)
                        {
                            rx = (float)rot[0]; ry = (float)rot[1]; rz = (float)rot[2];
                        }
                        asset.rooms[r].props[p].rotation = new Vector3(rx, ry, rz);

                        // Scale
                        float sx = 1f, sy = 1f, sz = 1f;
                        if (prop["scale"] is JArray scl && scl.Count >= 3)
                        {
                            sx = (float)scl[0]; sy = (float)scl[1]; sz = (float)scl[2];
                        }
                        asset.rooms[r].props[p].scale = new Vector3(sx, sy, sz);

                        asset.rooms[r].props[p].tag = prop["tag"]?.ToString() ?? "";
                    }
                }

                // Spawn points
                JArray spawns = room["spawnPoints"] as JArray;
                if (spawns != null)
                {
                    asset.rooms[r].spawnPoints = new LevelSpawnPoint[spawns.Count];
                    for (int s = 0; s < spawns.Count; s++)
                    {
                        JObject sp = spawns[s] as JObject;
                        asset.rooms[r].spawnPoints[s].position = Vector3.zero;
                        if (sp["position"] is JArray spPos && spPos.Count >= 3)
                        {
                            asset.rooms[r].spawnPoints[s].position = new Vector3(
                                (float)spPos[0], (float)spPos[1], (float)spPos[2]
                            );
                        }
                        asset.rooms[r].spawnPoints[s].team = sp["team"] != null ? sp["team"].Value<int>() : 1;
                        asset.rooms[r].spawnPoints[s].type = sp["type"]?.ToString() ?? "delta";
                    }
                }

                // Kill zones
                JArray kzs = room["killZones"] as JArray;
                if (kzs != null)
                {
                    asset.rooms[r].killZones = new LevelKillZone[kzs.Count];
                    for (int k = 0; k < kzs.Count; k++)
                    {
                        JObject kz = kzs[k] as JObject;
                        asset.rooms[r].killZones[k].position = Vector3.zero;
                        if (kz["position"] is JArray kzPos && kzPos.Count >= 3)
                        {
                            asset.rooms[r].killZones[k].position = new Vector3(
                                (float)kzPos[0], (float)kzPos[1], (float)kzPos[2]
                            );
                        }
                        asset.rooms[r].killZones[k].size = new Vector3(10f, 1f, 10f);
                        if (kz["size"] is JArray kzSize && kzSize.Count >= 3)
                        {
                            asset.rooms[r].killZones[k].size = new Vector3(
                                (float)kzSize[0], (float)kzSize[1], (float)kzSize[2]
                            );
                        }
                        asset.rooms[r].killZones[k].isTrigger = true;
                    }
                }
            }
        }

        // Global spawns
        JArray globalSpawns = layout["globalSpawnPoints"] as JArray;
        if (globalSpawns != null)
        {
            asset.globalSpawns = new GlobalSpawnData();
            asset.globalSpawns.spawnPoints = new LevelSpawnPoint[globalSpawns.Count];
            for (int g = 0; g < globalSpawns.Count; g++)
            {
                JObject sp = globalSpawns[g] as JObject;
                asset.globalSpawns.spawnPoints[g].position = Vector3.zero;
                if (sp["position"] is JArray spPos && spPos.Count >= 3)
                {
                    asset.globalSpawns.spawnPoints[g].position = new Vector3(
                        (float)spPos[0], (float)spPos[1], (float)spPos[2]
                    );
                }
                asset.globalSpawns.spawnPoints[g].team = sp["team"] != null ? sp["team"].Value<int>() : 1;
            }
        }

        // Save as Asset
        string assetPath = "Assets/LevelLayout.asset";
        AssetDatabase.CreateAsset(asset, assetPath);
        AssetDatabase.SaveAssets();
        Debug.Log("LEVEL_LAYOUT: Generated LevelLayout Asset at " + assetPath);
    }
}