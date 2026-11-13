using System.IO;
using UnityEngine;

public static class LevelBuilder
{
    [MenuItem("Tools/Build Level from Layout Asset")]
    public static void BuildFromLayoutAsset()
    {
        // Load the pre-generated LevelLayout Asset
        LevelLayout layout = Resources.Load<LevelLayout>("LevelLayout");
        if (layout == null)
        {
            Debug.LogError("LEVEL_BUILDER: No LevelLayout Asset found. Run 'Generate Level Layout Asset' first.");
            return;
        }

        Debug.Log("LEVEL_BUILDER: Building from Layout Asset '" + layout.levelName + "' v" + layout.version);

        GameObject root = new GameObject("LevelRoot_" + layout.levelName);

        // Process rooms
        if (layout.rooms != null)
        {
            foreach (LevelRoom room in layout.rooms)
            {
                if (string.IsNullOrEmpty(room.roomId)) continue;
                GameObject roomRoot = new GameObject("Room_" + room.roomId);
                roomRoot.transform.SetParent(root.transform);

                // Props
                if (room.props != null)
                {
                    foreach (LevelProp prop in room.props)
                    {
                        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path: prefabPath: prefabPath);
                        if (prefab == null) { Debug.LogWarning("LEVEL_BUILDER: Prefab not found: " + prefabPath); continue; }

                        GameObject instance = (GameObject)UnityEditor.PrefabUtility.InstantiatePrefab(prefab);
                        instance.transform.position = prop.position;
                        instance.transform.eulerAngles = prop.rotation;
                        instance.transform.localScale = prop.scale;
                        instance.transform.SetParent(roomRoot.transform);

                        if (!string.IsNullOrEmpty(prop.tag)) instance.tag = prop.tag;
                    }
                }

                // Spawn points
                if (room.spawnPoints != null)
                {
                    foreach (LevelSpawnPoint sp in room.spawnPoints)
                    {
                        GameObject spObj = new GameObject("SpawnPoint_T" + sp.team);
                        spObj.transform.position = sp.position;
                        spObj.transform.SetParent(roomRoot.transform);

                        var spawnComp = spObj.AddComponent(System.Type.GetType("bl_SpawnPoint"));
                        if (spawnComp != null)
                        {
                            var teamField = spawnComp.GetType().GetField("m_Team");
                            if (teamField != null) teamField.SetValue(spawnComp, sp.team);
                        }
                    }
                }

                // Kill zones
                if (room.killZones != null)
                {
                    foreach (LevelKillZone kz in room.killZones)
                    {
                        GameObject kzObj = new GameObject("KillZone");
                        kzObj.transform.position = kz.position;
                        kzObj.transform.SetParent(roomRoot.transform);
                        BoxCollider bc = kzObj.AddComponent<BoxCollider>();
                        bc.size = kz.size;
                        bc.isTrigger = kz.isTrigger;
                    }
                }
            }
        }

        // Global spawn points
        if (layout.globalSpawns != null && layout.globalSpawns.spawnPoints != null)
        {
            GameObject globalRoot = new GameObject("GlobalSpawnPoints");
            globalRoot.transform.SetParent(root.transform);
            foreach (LevelSpawnPoint sp in layout.globalSpawns.spawnPoints)
            {
                GameObject spObj = new GameObject("GlobalSpawn_T" + sp.team);
                spObj.transform.position = sp.position;
                spObj.transform.SetParent(globalRoot.transform);
            }
        }

        UnityEditor.EditorUtility.SetDirty(root);
        Debug.Log("LEVEL_BUILDER: Level built from asset '" + layout.levelName + "'. Root: " + root.name);
    }
}