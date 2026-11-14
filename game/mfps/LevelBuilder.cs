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
    static readonly System.Collections.Generic.List<Vector3> spawnPositions = new System.Collections.Generic.List<Vector3>();

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
        spawnPositions.Clear();
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
                    // The vault door prefab embeds its closed round Lid AND a frame collider that can seal
                    // the 5m doorway. Make the vault passable: disable the Lid visual and drop all
                    // colliders belonging to the frame instance (walls around it keep the room sealed).
                    if (inst.name.Contains("VaultDoor_Frame"))
                    {
                        int lids = 0;
                        foreach (Transform child in inst.transform)
                        {
                            if (child.name.Contains("Lid"))
                            {
                                child.gameObject.SetActive(false);
                                lids++;
                            }
                        }
                        int cols = 0;
                        foreach (Collider c in inst.GetComponentsInChildren<Collider>(true))
                        {
                            UnityEngine.Object.DestroyImmediate(c);
                            cols++;
                        }
                        Debug.Log("LEVEL_BUILDER: vault opened lids=" + lids + " collidersRemoved=" + cols +
                            " children=" + inst.transform.childCount);
                    }
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
        // Gameplay geometry stays on Default (0) so MFPS AI/weapon raycasts hit walls.
        // Only ceilings/roof go to layer 9 (NoNav) and are excluded from the bake.
        SetNoNavLayerRecursive(levelRoot.transform);

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

        // Bake NavMesh via the Unity 6 AI Navigation package (legacy NavMeshBuilder no-ops in Unity 6),
        // then save again so the baked data ships with the scene.
        try
        {
            GameObject navGo = new GameObject("NavMeshSurface");
            SceneManager.MoveGameObjectToScene(navGo, scene);
            var surface = navGo.AddComponent<Unity.AI.Navigation.NavMeshSurface>();
            surface.collectObjects = Unity.AI.Navigation.CollectObjects.All;
            surface.useGeometry = UnityEngine.AI.NavMeshCollectGeometry.PhysicsColliders;
            // Bake ground geometry only: everything except the NoNav layer (ceilings/roof, layer 9).
            // Gameplay objects stay on Default so AI/weapon raycasts collide with walls normally.
            surface.layerMask = ~(1 << 9);
            surface.BuildNavMesh();
            EditorSceneManager.SaveScene(scene, savePath);
            Debug.Log("LEVEL_BUILDER: NavMeshSurface baked+saved");
        }
        catch (System.Exception e)
        {
            Debug.LogWarning("LEVEL_BUILDER: NavMeshSurface bake failed (non-fatal): " + e.Message);
        }

        // Dump the baked navmesh triangles for offline visualisation (specs/render_navmesh.py)
        try
        {
            var tri = UnityEngine.AI.NavMesh.CalculateTriangulation();
            var sb = new System.Text.StringBuilder();
            sb.Append("{\"vertices\":[");
            for (int i = 0; i < tri.vertices.Length; i++)
            {
                if (i > 0) sb.Append(",");
                sb.Append("[").Append(Fmt(tri.vertices[i].x)).Append(",")
                  .Append(Fmt(tri.vertices[i].y)).Append(",")
                  .Append(Fmt(tri.vertices[i].z)).Append("]");
            }
            sb.Append("],\"indices\":[");
            for (int i = 0; i < tri.indices.Length; i++)
            {
                if (i > 0) sb.Append(",");
                sb.Append(tri.indices[i]);
            }
            sb.Append("]}");
            File.WriteAllText("/content/navmesh.json", sb.ToString());
            Debug.Log("NAVMESH_DUMP verts=" + tri.vertices.Length + " tris=" + (tri.indices.Length / 3));
        }
        catch (System.Exception e)
        {
            Debug.LogWarning("NAVMESH_DUMP_FAIL " + e.Message);
        }

        // Integrity gate 1: every spawn point and room centre must be mutually reachable on the NavMesh
        try
        {
            var tri = UnityEngine.AI.NavMesh.CalculateTriangulation();
            Debug.Log("NAVMESH_VERIFY tris=" + (tri.indices.Length / 3) + " verts=" + tri.vertices.Length);
            if (tri.vertices.Length > 0)
            {
                Vector3 mn = tri.vertices[0], mx = tri.vertices[0];
                foreach (Vector3 v in tri.vertices)
                {
                    mn = Vector3.Min(mn, v);
                    mx = Vector3.Max(mx, v);
                }
                Debug.Log("NAVMESH_BOUNDS min=" + mn.ToString("F1") + " max=" + mx.ToString("F1"));
            }
        }
        catch (System.Exception e)
        {
            Debug.LogWarning("NAVMESH_VERIFY_FAIL " + e.Message);
        }

        var navPoints = new System.Collections.Generic.List<Vector3>(spawnPositions);
        // Probe each room at its first designed cover point (clear floor), not the geometric centre
        // (centres can land inside desk/case pockets and falsely fail the gate).
        foreach (LevelRoomData room in layout.rooms)
        {
            if (room == null || room.coverPoints == null || room.coverPoints.Length == 0) continue;
            Vector3 cp = ToV3(room.coverPoints[0].position, Vector3.zero);
            cp.y = 0.4f;
            navPoints.Add(cp);
        }
        for (int i = 0; i < navPoints.Count; i++)
        {
            UnityEngine.AI.NavMeshHit hit;
            bool ok = UnityEngine.AI.NavMesh.SamplePosition(navPoints[i], out hit, 3f, UnityEngine.AI.NavMesh.AllAreas);
            Debug.Log("NAVPOINT " + i + " " + navPoints[i].ToString("F1") +
                (ok ? (" -> " + hit.position.ToString("F1")) : " NO_SAMPLE"));
        }
        int navPairs = 0;
        int navFails = 0;
        for (int i = 0; i < navPoints.Count; i++)
        {
            for (int j = i + 1; j < navPoints.Count; j++)
            {
                navPairs++;
                UnityEngine.AI.NavMeshPath path = new UnityEngine.AI.NavMeshPath();
                string failReason = NavReachableDetail(navPoints[i], navPoints[j], path);
                if (failReason != null)
                {
                    navFails++;
                    Debug.LogWarning("NAV_CONNECT_FAIL " + i + "->" + j + " reason=" + failReason);
                }
            }
        }
        Debug.Log("LEVEL_BUILDER: nav connectivity fails=" + navFails + "/" + navPairs);
        if (navFails > 0)
        {
            Debug.LogError("NAV_CONNECT_FAILED total=" + navFails);
        }

        // Integrity gate 2: report colliders with no renderer (invisible-wall suspects)
        int invisible = 0;
        foreach (Collider col in UnityEngine.Object.FindObjectsByType<Collider>(FindObjectsSortMode.None))
        {
            if (col == null) continue;
            if (col.GetComponent<Renderer>() != null) continue;
            if (col.GetComponentInChildren<Renderer>() != null) continue;
            string n = col.gameObject.name;
            if (n.Contains("KillZone") || n.Contains("Spawn") || n.Contains("Manager") ||
                n.Contains("UI") || n.Contains("Canvas") || n.Contains("Floor")) continue;
            invisible++;
            Debug.LogWarning("INVISIBLE_COLLIDER " + n + " (" + col.GetType().Name + ")");
        }
        Debug.Log("LEVEL_BUILDER: invisible colliders=" + invisible);

        // Integrity gate 3: sightlines. Walls must block listed lines; openings must stay clear.
        int losFails = 0;
        int losCount = 0;
        if (layout.losChecks != null)
        {
            foreach (LevelLosCheckData chk in layout.losChecks)
            {
                if (chk == null) continue;
                losCount++;
                Vector3 a = ToV3(chk.from, new Vector3(0f, 0.8f, 0f));
                Vector3 b = ToV3(chk.to, new Vector3(0f, 0.8f, 0f));
                UnityEngine.RaycastHit hitInfo;
                bool blocked = Physics.Linecast(a, b, out hitInfo, 1 << 0);
                if (blocked != chk.blocked)
                {
                    losFails++;
                    Debug.LogWarning("LOS_FAIL " + chk.name + " blocked=" + blocked +
                        " expected=" + chk.blocked + (blocked ? (" hit=" + hitInfo.collider.name) : ""));
                }
            }
        }
        Debug.Log("LEVEL_BUILDER: los fails=" + losFails + "/" + losCount);
        if (losFails > 0)
        {
            Debug.LogError("LOS_GATE_FAILED total=" + losFails);
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
        spawnPositions.Add(obj.transform.position);
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

    static string Fmt(float v)
    {
        return v.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture);
    }

    static Vector3 ToV3(float[] a, Vector3 def)
    {
        if (a != null && a.Length >= 3) return new Vector3(a[0], a[1], a[2]);
        return def;
    }

    // Both points snapped onto the NavMesh, then a complete path must exist.
    // Returns null when reachable, otherwise a diagnostic reason.
    static string NavReachableDetail(Vector3 a, Vector3 b, UnityEngine.AI.NavMeshPath path)
    {
        UnityEngine.AI.NavMeshHit ha;
        UnityEngine.AI.NavMeshHit hb;
        if (!UnityEngine.AI.NavMesh.SamplePosition(a, out ha, 3f, UnityEngine.AI.NavMesh.AllAreas)) return "sampleA";
        if (!UnityEngine.AI.NavMesh.SamplePosition(b, out hb, 3f, UnityEngine.AI.NavMesh.AllAreas)) return "sampleB";
        bool ok = UnityEngine.AI.NavMesh.CalculatePath(ha.position, hb.position, UnityEngine.AI.NavMesh.AllAreas, path);
        if (!ok) return "calc";
        if (path.status != UnityEngine.AI.NavMeshPathStatus.PathComplete) return path.status.ToString();
        return null;
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

    // Layer 9 (NoNav): ceilings/roof, excluded from the navmesh bake. Everything else stays on
    // Default (layer 0) so MFPS AI LOS and weapon raycasts collide with walls, props and floors.
    static void SetNoNavLayerRecursive(Transform t)
    {
        foreach (Transform child in t)
        {
            bool noNav = child.name.Contains("Ceiling") || child.name.Contains("Roof");
            child.gameObject.layer = noNav ? 9 : 0;
            SetNoNavLayerRecursive(child);
        }
    }
}
