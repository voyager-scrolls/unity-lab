using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

// Builds the level scene from a LevelLayout asset and wires the full MFPS
// gameplay layer (GameManager, AIManager, ItemManager, UI, spawn points,
// KillZone) using the recipe proven in heist-t1-5.
public static class LevelBuilder
{
    static int spawnCounter;

    public static void BuildFromLayoutAsset()
    {
        LevelLayout layout = Resources.Load<LevelLayout>("LevelLayout");
        if (layout == null || layout.rooms == null)
        {
            throw new Exception("LEVEL_BUILDER: LevelLayout asset missing. Run LevelLayoutGenerator.Generate first.");
        }

        Debug.Log("LEVEL_BUILDER: building '" + layout.levelName + "' v" + layout.version + " rooms=" + layout.rooms.Length);

        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        // Floor so nothing falls through the grey plane
        GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
        floor.name = "Floor";
        floor.transform.position = new Vector3(0f, 0f, 0f);
        floor.transform.localScale = new Vector3(20f, 1f, 20f);

        GameObject levelRoot = new GameObject("LevelRoot_" + layout.levelName.Replace(" ", "_"));
        spawnCounter = 0;

        foreach (LevelRoomData room in layout.rooms)
        {
            if (room == null || string.IsNullOrEmpty(room.roomId)) continue;
            GameObject roomRoot = new GameObject("Room_" + room.roomId);
            roomRoot.transform.SetParent(levelRoot.transform, false);

            if (room.props != null)
            {
                foreach (LevelPropData prop in room.props)
                {
                    if (prop == null || string.IsNullOrEmpty(prop.prefabPath)) continue;
                    GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prop.prefabPath);
                    if (prefab == null)
                    {
                        Debug.LogWarning("LEVEL_BUILDER: prefab not found: " + prop.prefabPath);
                        continue;
                    }
                    GameObject inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                    inst.transform.position = ToV3(prop.position, Vector3.zero);
                    inst.transform.eulerAngles = ToV3(prop.rotation, Vector3.zero);
                    inst.transform.localScale = ToV3(prop.scale, Vector3.one);
                    inst.transform.SetParent(roomRoot.transform, true);
                }
            }

            if (room.spawnPoints != null)
            {
                foreach (LevelSpawnPointData sp in room.spawnPoints)
                {
                    CreateSpawnPoint(sp, scene);
                }
            }
        }

        if (layout.globalSpawnPoints != null)
        {
            foreach (LevelSpawnPointData sp in layout.globalSpawnPoints)
            {
                CreateSpawnPoint(sp, scene);
            }
        }

        // MFPS wiring (heist-t1-5 recipe)
        InstantiateMfpsPrefab(scene, "Assets/MFPS/Content/Prefabs/Network/GameManager.prefab", "GameManager");
        InstantiateMfpsPrefab(scene, "Assets/MFPS/Content/Prefabs/GamePlay/AIManager.prefab", "AIManager");
        InstantiateMfpsPrefab(scene, "Assets/MFPS/Content/Prefabs/GamePlay/ItemManager.prefab", "ItemManager");
        InstantiateMfpsPrefab(scene, "Assets/MFPS/Content/Prefabs/UI/UI.prefab", "UI");

        GameObject gameModes = new GameObject("GameModes");
        gameModes.transform.position = Vector3.zero;

        string kzPath = "Assets/MFPS/Content/Prefabs/GamePlay/Level/KillZone.prefab";
        GameObject kzPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(kzPath);
        if (kzPrefab != null)
        {
            GameObject kz = (GameObject)PrefabUtility.InstantiatePrefab(kzPrefab, scene);
            kz.transform.position = new Vector3(0f, -5f, 0f);
            kz.transform.localScale = new Vector3(200f, 1f, 200f);
            Debug.Log("LEVEL_BUILDER: KillZone placed");
        }
        else
        {
            Debug.LogWarning("LEVEL_BUILDER: KillZone prefab not found: " + kzPath);
        }

        // Save + register the scene for the player build
        string savePath = "Assets/MFPS/Scenes/HeistLevel.unity";
        Directory.CreateDirectory("Assets/MFPS/Scenes");
        EditorSceneManager.SaveScene(scene, savePath);

        var buildScenes = new System.Collections.Generic.List<EditorBuildSettingsScene>();
        buildScenes.Add(new EditorBuildSettingsScene(savePath, true));
        EditorBuildSettings.scenes = buildScenes.ToArray();

        Debug.Log("LEVEL_BUILDER: scene saved " + savePath + " spawns=" + spawnCounter + " BUILD_SCENES_SET");
    }

    static void CreateSpawnPoint(LevelSpawnPointData sp, Scene scene)
    {
        if (sp == null) return;
        string name = "DeltaSpawn_" + spawnCounter;
        spawnCounter++;
        GameObject obj = new GameObject(name);
        SceneManager.MoveGameObjectToScene(obj, scene);
        obj.transform.position = ToV3(sp.position, new Vector3(0f, 1f, 0f));
        bl_SpawnPoint bsp = obj.AddComponent<bl_SpawnPoint>();
        int team = sp.team <= 0 ? 1 : sp.team;
        bsp.m_Team = (global::Team)team;
        Debug.Log("LEVEL_BUILDER: spawn " + name + " team=" + team + " type=" + sp.type);
    }

    static void InstantiateMfpsPrefab(Scene scene, string path, string goName)
    {
        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (prefab == null)
        {
            throw new Exception("LEVEL_BUILDER: missing MFPS prefab " + path);
        }
        GameObject inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
        inst.transform.position = Vector3.zero;
        inst.name = goName;
        Debug.Log("LEVEL_BUILDER: wired " + goName);
    }

    static Vector3 ToV3(float[] a, Vector3 def)
    {
        if (a != null && a.Length >= 3) return new Vector3(a[0], a[1], a[2]);
        return def;
    }
}
