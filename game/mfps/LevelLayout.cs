using System;
using System.IO;
using Newtonsoft.Json;
using UnityEngine;

// Data classes deserialized from the level layout JSON (specs/heist-bank-v1.json).
// Positions are float[] because JSON arrays cannot map onto UnityEngine.Vector3.
// Newtonsoft.Json is used because it is referenced by the Unity project
// (com.unity.nuget.newtonsoft-json) and compiles green in this pipeline.
public class LevelLayoutData
{
    [JsonProperty("name")]
    public string levelName;
    [JsonProperty("version")]
    public int version;
    [JsonProperty("description")]
    public string description;
    [JsonProperty("rooms")]
    public LevelRoomData[] rooms;
    [JsonProperty("globalSpawnPoints")]
    public LevelSpawnPointData[] globalSpawnPoints;
    [JsonProperty("losChecks")]
    public LevelLosCheckData[] losChecks;
}

[System.Serializable]
public class LevelLosCheckData
{
    [JsonProperty("name")]
    public string name;
    [JsonProperty("from")]
    public float[] from;
    [JsonProperty("to")]
    public float[] to;
    [JsonProperty("blocked")]
    public bool blocked;
}

[System.Serializable]
public class LevelBoundsData
{
    [JsonProperty("min")]
    public float[] min;
    [JsonProperty("max")]
    public float[] max;
}

[System.Serializable]
public class LevelRoomData
{
    [JsonProperty("id")]
    public string roomId;
    [JsonProperty("bounds")]
    public LevelBoundsData bounds;
    [JsonProperty("props")]
    public LevelPropData[] props;
    [JsonProperty("spawnPoints")]
    public LevelSpawnPointData[] spawnPoints;
    [JsonProperty("coverPoints")]
    public LevelCoverPointData[] coverPoints;
    [JsonProperty("killZones")]
    public LevelKillZoneData[] killZones;
}

[System.Serializable]
public class LevelCoverPointData
{
    [JsonProperty("position")]
    public float[] position;
}

[System.Serializable]
public class LevelPropData
{
    [JsonProperty("prefab")]
    public string prefabPath;
    [JsonProperty("position")]
    public float[] position;
    [JsonProperty("rotation")]
    public float[] rotation;
    [JsonProperty("scale")]
    public float[] scale;
    [JsonProperty("tag")]
    public string tag;
}

[System.Serializable]
public class LevelSpawnPointData
{
    [JsonProperty("position")]
    public float[] position;
    [JsonProperty("team")]
    public int team;
    [JsonProperty("type")]
    public string type;
}

[System.Serializable]
public class LevelKillZoneData
{
    [JsonProperty("position")]
    public float[] position;
    [JsonProperty("size")]
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
    public LevelLosCheckData[] losChecks;
    public string layoutJsonPath;
}

#if UNITY_EDITOR
public static class LevelLayoutGenerator
{
    public static void Generate()
    {
        string jsonPath = "/content/level-layout.json";
        if (!File.Exists(jsonPath))
        {
            Debug.LogError("LEVEL_LAYOUT: no layout file at " + jsonPath);
            throw new Exception("LEVEL_LAYOUT: no layout file at " + jsonPath);
        }

        string json = File.ReadAllText(jsonPath);
        LevelLayoutData data = JsonConvert.DeserializeObject<LevelLayoutData>(json);
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
        asset.losChecks = data.losChecks;
        asset.layoutJsonPath = jsonPath;

        System.IO.Directory.CreateDirectory("Assets/Resources");
        string assetPath = "Assets/Resources/LevelLayout.asset";
        UnityEditor.AssetDatabase.CreateAsset(asset, assetPath);
        UnityEditor.AssetDatabase.SaveAssets();
        LevelLayout verify = Resources.Load<LevelLayout>("LevelLayout");
        if (verify == null || verify.rooms == null || verify.rooms.Length == 0)
        {
            throw new Exception("LEVEL_LAYOUT: asset did not serialize rooms (verify=" +
                (verify == null ? "LOAD_FAIL" : "rooms_null") + ")");
        }
        Debug.Log("LEVEL_LAYOUT: generated " + assetPath + " name=" + asset.levelName +
            " rooms=" + asset.rooms.Length + " VERIFY_ROOMS=" + verify.rooms.Length);
    }
}
#endif
