#if UNITY_EDITOR
using UnityEngine;
using UnityEngine.AI;
using UnityEditor;
using UnityEditor.SceneManagement;
using System.IO;

public static class HeistSceneBuilder
{
    [MenuItem("MFPS/Build Heist Level")]
    public static void Build()
    {
        string src = "Assets/PolygonHeist/Scenes/Layout.unity";
        string dst = "Assets/MFPS/Scenes/HeistLevel.unity";

        if (!File.Exists(src))
        {
            Debug.LogError("HEIST_LAYOUT_MISSING: " + src);
            return;
        }

        var scene = EditorSceneManager.OpenScene(src, OpenSceneMode.Single);

        // Add spawn points (bl_SpawnPoint, Team All) at a few positions.
        Vector3[] spPos = new Vector3[] {
            new Vector3(0f, 1f, 0f),
            new Vector3(8f, 1f, 8f),
            new Vector3(-8f, 1f, -8f),
            new Vector3(0f, 1f, -12f)
        };
        for (int i = 0; i < spPos.Length; i++)
        {
            var go = new GameObject("DeltaSpawn_" + i);
            go.transform.position = spPos[i];
            go.AddComponent<bl_SpawnPoint>();
        }

        // Add a KillZone below the floor (instantiate prefab if available).
        string kzPath = "Assets/MFPS/Content/Prefabs/GamePlay/Level/KillZone.prefab";
        if (File.Exists(kzPath))
        {
            var kzPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(kzPath);
            if (kzPrefab != null)
            {
                var kz = (GameObject)PrefabUtility.InstantiatePrefab(kzPrefab, scene);
                kz.transform.position = new Vector3(0f, -5f, 0f);
                kz.transform.localScale = new Vector3(200f, 1f, 200f);
                Debug.Log("HEIST_KILLZONE_ADDED");
            }
        }

        // Bake NavMesh (best-effort; legacy builder).
        try
        {
            NavMeshBuilder.BuildNavMesh();
            Debug.Log("HEIST_NAVMESH_BAKED");
        }
        catch (System.Exception e)
        {
            Debug.LogWarning("HEIST_NAVMESH_FAILED: " + e.Message);
        }

        // Save as new scene.
        Directory.CreateDirectory(Path.GetDirectoryName(dst));
        EditorSceneManager.SaveScene(scene, dst);
        Debug.Log("HEIST_LEVEL_SAVED: " + dst);

        // Set build scene list to HeistLevel only.
        var buildScenes = new[] { new EditorBuildSettingsScene(dst, true) };
        EditorBuildSettings.scenes = buildScenes;
        Debug.Log("HEIST_BUILD_SCENE_SET");

        // Save assets.
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("HEIST_DONE");
    }
}
#endif
