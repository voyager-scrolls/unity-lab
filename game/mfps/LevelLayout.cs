using System;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using UnityEngine;

// Data classes deserialized from the level layout JSON (specs/heist-bank-v1.json).
// Positions are float[] because System.Text.Json cannot map a JSON array onto UnityEngine.Vector3.
public class LevelLayoutData
{
    [JsonPropertyName("name")]
    public string levelName;
    [JsonPropertyName("version")]
    public int version;
    [JsonPropertyName("description")]
    public string description;
    [JsonPropertyName("rooms")]
    public LevelRoomData[] rooms;
    [JsonPropertyName("globalSpawnPoints")]
    public LevelSpawnPointData[] globalSpawnPoints;
}

public class LevelRoomData
{
    [JsonPropertyName("id")]
    public string roomId;
    [JsonPropertyName("props")]
    public LevelPropData[] props;
    [JsonPropertyName("spawnPoints")]
    public LevelSpawnPointData[] spawnPoints;
    [JsonPropertyName("killZones")]
    public LevelKillZoneData[] killZones;
}

public class LevelPropData
{
    [JsonPropertyName("prefab")]
    public string prefabPath;
    [JsonPropertyName("position")]
    public float[] position;
    [JsonPropertyName("rotation")]
    public float[] rotation;
    [JsonPropertyName("scale")]
    public float[] scale;
    [JsonPropertyName("tag")]
    public string tag;
}

public class LevelSpawnPointData
{
    [JsonPropertyName("position")]
    public float[] position;
    [JsonPropertyName("team")]
    public int team;
    [JsonPropertyName("type")]
    public string type;
}

public class LevelKillZoneData
{
    [JsonPropertyName("position")]
    public float[] position;
    [JsonPropertyName("size")]
    public float[] size;
}

// ScriptableObject mirror of the layout data; saved as an asset that the
// scene builder reads. Lives in Assets/Editor (editor-only pipeline).
public class LevelLayout : ScriptableObject
{
    public string levelName;
    public int version;
    public string description;
    public LevelRoomData[] rooms;
    public LevelSpawnPointData[] globalSpawnPoints;
    public string layoutJsonPath;
}

#if UNITY_EDITOR
public static class LevelLayoutGenerator
{
    static readonly JsonSerializerOptions JsonOpts = new JsonSerializerOptions
    {
        PropertyNameCaseInsensitive = true,
        IncludeFields = true
    };

    public static void Generate()
    {
        string jsonPath = "/content/level-layout.json";
        if (!File.Exists(jsonPath))
        {
            Debug.LogError("LEVEL_LAYOUT: no layout file at " + jsonPath);
            throw new Exception("LEVEL_LAYOUT: no layout file at " + jsonPath);
        }

        string json = File.ReadAllText(jsonPath);
        LevelLayoutData data = JsonSerializer.Deserialize<LevelLayoutData>(json, JsonOpts);
        if (data == null || data.rooms == null || data.rooms.Length == 0)
        {
            throw new Exception("LEVEL_LAYOUT: failed to deserialize layout JSON");
        }

        LevelLayout asset = ScriptableObject.CreateInstance<LevelLayout>();
        asset.levelName = string.IsNullOrEmpty(data.levelName) ? "Unnamed" : data.levelName;
        asset.version = data.version;
        asset.description = data.description;
        asset.rooms = data.rooms;
        asset.globalSpawnPoints = data.globalSpawnPoints;
        asset.layoutJsonPath = jsonPath;

        System.IO.Directory.CreateDirectory("Assets/Resources");
        string assetPath = "Assets/Resources/LevelLayout.asset";
        UnityEditor.AssetDatabase.CreateAsset(asset, assetPath);
        UnityEditor.AssetDatabase.SaveAssets();
        Debug.Log("LEVEL_LAYOUT: generated " + assetPath + " name=" + asset.levelName + " rooms=" + asset.rooms.Length);
    }
}
#endif
