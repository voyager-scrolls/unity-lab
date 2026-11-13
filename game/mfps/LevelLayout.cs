using System.IO;
using System.Text.Json;
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
    public Bounds bounds; // min/max extents
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
    public Vector3 size; // extents for BoxCollider (half-sizes)
    public bool isTrigger = true;
}

[System.Serializable]
public class GlobalSpawnData
{
    public LevelSpawnPoint[] spawnPoints;
}

public static class LevelLayoutGenerator
{
    private static readonly JsonSerializerOptions JsonOpts = new JsonSerializerOptions
    {
        PropertyNameCaseInsensitive = true
    };

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
        LevelLayout asset = JsonSerializer.Deserialize<LevelLayout>(json, JsonOpts);

        if (asset == null)
        {
            Debug.LogError("LEVEL_LAYOUT: Failed to deserialize LevelLayout from JSON");
            return;
        }

        asset.layoutJsonPath = jsonPath;

        // Save as Asset
        string assetPath = "Assets/LevelLayout.asset";
        AssetDatabase.CreateAsset(asset, assetPath);
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("LEVEL_LAYOUT: Generated LevelLayout Asset at " + assetPath + " (" + asset.rooms.Length + " rooms)");
    }
}