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
            throw new Exception("LEVEL_BUILDER: LevelLayout asset unusable (loaded=" + (layout != null) +
                " rooms_null=" + (layout != null && layout.rooms == null) + "). Run LevelLayoutGenerator.Generate first.");
        }

        Debug.Log("LEVEL_BUILDER: building '" + layout.levelName + "' v" + layout.version + " rooms=" + layout.rooms.Length);

        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        // Floor so nothing falls through the grey plane
        GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
        floor.name = "Floor";
        floor.transform.position = new Vector3(0f, -0.05f, 0f);
        floor.transform.localScale = new Vector3(20f, 1f, 20f);

        // Sun + ambient so the scene is not flat grey
        GameObject sunGo = new GameObject("Sun");
        Light sun = sunGo.AddComponent<Light>();
        sun.type = LightType.Directional;
        sun.intensity = 1.15f;
        sun.color = new Color(1f, 0.95f, 0.88f);
        sun.shadows = LightShadows.Soft;
        sunGo.transform.rotation = Quaternion.Euler(52f, -35f, 0f);
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.68f, 0.66f, 0.62f);
        RenderSettings.ambientEquatorColor = new Color(0.55f, 0.51f, 0.46f);
        RenderSettings.ambientGroundColor = new Color(0.34f, 0.31f, 0.27f);
        Debug.Log("LEVEL_BUILDER: lighting set (sun + warm trilight ambient)");

        GameObject levelRoot = new GameObject("LevelRoot_" + layout.levelName.Replace(" ", "_"));
        spawnCounter = 0;
        int placed = 0;
        int missing = 0;

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
                        missing++;
                        continue;
                    }
                    GameObject inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                    inst.transform.position = ToV3(prop.position, Vector3.zero);
                    inst.transform.eulerAngles = ToV3(prop.rotation, Vector3.zero);
                    inst.transform.localScale = ToV3(prop.scale, Vector3.one);
                    inst.transform.SetParent(roomRoot.transform, true);
                    placed++;
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
        GameObject aiManager = InstantiateMfpsPrefab(scene, "Assets/MFPS/Content/Prefabs/GamePlay/AIManager.prefab", "AIManager");
        InstantiateMfpsPrefab(scene, "Assets/MFPS/Content/Prefabs/GamePlay/ItemManager.prefab", "ItemManager");
        InstantiateMfpsPrefab(scene, "Assets/MFPS/Content/Prefabs/UI/UI.prefab", "UI");

        // AI cover points (bots seek these via bl_AICovertPointManager; no points = no pursuit)
        int coverCount = 0;
        foreach (LevelRoomData room in layout.rooms)
        {
            if (room == null || room.coverPoints == null) continue;
            foreach (LevelCoverPointData cp in room.coverPoints)
            {
                if (cp == null) continue;
                GameObject cpObj = new GameObject("CoverPoint_" + coverCount);
                SceneManager.MoveGameObjectToScene(cpObj, scene);
                cpObj.transform.SetParent(aiManager.transform, true);
                cpObj.transform.position = ToV3(cp.position, new Vector3(0f, 0.1f, 0f));
                cpObj.AddComponent<bl_AICoverPoint>();
                coverCount++;
            }
        }
        Debug.Log("LEVEL_BUILDER: cover points=" + coverCount);

        GameObject gameModes = new GameObject("GameModes");
        gameModes.transform.position = Vector3.zero;

        // Mark level geometry static and bake later (after first save, so the
        // baked navmesh has a scene path and is stored with the scene)
        floor.isStatic = true;
        levelRoot.isStatic = true;
        MarkStaticRecursive(levelRoot.transform);

        // Assign Photon scene-view IDs (PUN needs 1..999 for scene objects; ID 0 breaks
        // RPC delivery -> countdown never finishes -> player never spawns)
        Photon.Pun.PhotonView[] pvs = UnityEngine.Object.FindObjectsByType<Photon.Pun.PhotonView>(FindObjectsSortMode.None);
        int sid = 1;
        foreach (Photon.Pun.PhotonView pv in pvs)
        {
            if (pv == null) continue;
            if (pv.Owner == null && pv.ViewID == 0)
            {
                pv.ViewID = sid;
                sid++;
            }
        }
        Debug.Log("LEVEL_BUILDER: photon scene views assigned=" + (sid - 1));

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

        // Bake NavMesh only now that the scene has a path, then save again so the
        // baked data ships with the scene (baking an unsaved scene silently discards it)
        try
        {
            UnityEditor.AI.NavMeshBuilder.BuildNavMesh();
            EditorSceneManager.SaveScene(scene, savePath);
            Debug.Log("LEVEL_BUILDER: NavMesh baked+saved");
        }
        catch (System.Exception e)
        {
            Debug.LogWarning("LEVEL_BUILDER: NavMesh bake failed (non-fatal): " + e.Message);
        }

        var buildScenes = new System.Collections.Generic.List<EditorBuildSettingsScene>();
        string mainMenuPath = "Assets/MFPS/Scenes/MainMenu.unity";
        if (File.Exists(mainMenuPath))
        {
            buildScenes.Add(new EditorBuildSettingsScene(mainMenuPath, true));
            Debug.Log("LEVEL_BUILDER: MainMenu added to build list (safety)");
        }
        buildScenes.Add(new EditorBuildSettingsScene(savePath, true));
        EditorBuildSettings.scenes = buildScenes.ToArray();

        Debug.Log("LEVEL_BUILDER: scene saved " + savePath + " spawns=" + spawnCounter +
            " props=" + placed + " missing=" + missing + " BUILD_SCENES_SET");
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

    static GameObject InstantiateMfpsPrefab(Scene scene, string path, string goName)
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
        return inst;
    }

    static Vector3 ToV3(float[] a, Vector3 def)
    {
        if (a != null && a.Length >= 3) return new Vector3(a[0], a[1], a[2]);
        return def;
    }

    static void MarkStaticRecursive(Transform t)
    {
        foreach (Transform child in t)
        {
            bool skip = child.name.Contains("Ceiling") || child.name.Contains("Roof");
            child.gameObject.isStatic = !skip;
            MarkStaticRecursive(child);
        }
    }
}
