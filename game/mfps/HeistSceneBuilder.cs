using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.SceneManagement;

namespace CoverShooter
{
    public static class HeistSceneBuilder
    {
        [MenuItem("MFPS/Build Heist Level Scene")]
        public static void BuildHeistScene()
        {
            // Open the Synty Heist layout scene
            string layoutPath = "Assets/PolygonHeist/Scenes/Layout.unity";
            if (!File.Exists(layoutPath))
            {
                Debug.LogError("Layout scene not found: " + layoutPath);
                return;
            }
            var scene = EditorSceneManager.OpenScene(layoutPath, OpenSceneMode.Single);

            // Instantiate GameManager prefab (position 0,0,0 like ExampleLevel)
            string gmPath = "Assets/MFPS/Content/Prefabs/Network/GameManager.prefab";
            var gmPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(gmPath);
            if (gmPrefab != null)
            {
                var gm = PrefabUtility.InstantiatePrefab(gmPrefab, scene) as GameObject;
                gm.transform.position = Vector3.zero;
                gm.name = "GameManager";
                Debug.Log("INSTANTIATED: GameManager");
            }
            else
            {
                Debug.LogError("GameManager prefab not found: " + gmPath);
            }

            // Instantiate AIManager prefab
            string aiPath = "Assets/MFPS/Content/Prefabs/GamePlay/AIManager.prefab";
            var aiPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(aiPath);
            if (aiPrefab != null)
            {
                var ai = PrefabUtility.InstantiatePrefab(aiPrefab, scene) as GameObject;
                ai.transform.position = Vector3.zero;
                ai.name = "AIManager";
                Debug.Log("INSTANTIATED: AIManager");
            }
            else
            {
                Debug.LogError("AIManager prefab not found: " + aiPath);
            }

            // Instantiate ItemManager prefab
            string itemPath = "Assets/MFPS/Content/Prefabs/GamePlay/ItemManager.prefab";
            var itemPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(itemPath);
            if (itemPrefab != null)
            {
                var item = PrefabUtility.InstantiatePrefab(itemPrefab, scene) as GameObject;
                item.transform.position = Vector3.zero;
                item.name = "ItemManager";
                Debug.Log("INSTANTIATED: ItemManager");
            }
            else
            {
                Debug.LogError("ItemManager prefab not found: " + itemPath);
            }

            // Instantiate UI prefab (contains bl_UIReferences)
            string uiPath = "Assets/MFPS/Content/Prefabs/UI/UI.prefab";
            var uiPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(uiPath);
            if (uiPrefab != null)
            {
                var ui = PrefabUtility.InstantiatePrefab(uiPrefab, scene) as GameObject;
                ui.transform.position = Vector3.zero;
                ui.name = "UI";
                Debug.Log("INSTANTIATED: UI");
            }
            else
            {
                Debug.LogError("UI prefab not found: " + uiPath);
            }

            // Create GameModes empty GameObject
            var gameModes = new GameObject("GameModes");
            SceneManager.MoveGameObjectToScene(gameModes, scene);
            gameModes.transform.position = Vector3.zero;
            Debug.Log("CREATED: GameModes");

            // Add spawn points if they don't exist
            if (GameObject.Find("DeltaSpawn_0") == null)
            {
                var sp0 = new GameObject("DeltaSpawn_0");
                SceneManager.MoveGameObjectToScene(sp0, scene);
                sp0.transform.position = new Vector3(0, 1, 0);
                var bsp0 = sp0.AddComponent<bl_SpawnPoint>();
                bsp0.m_Team = (global::Team)1;
                Debug.Log("CREATED: DeltaSpawn_0 (Team1)");
            }
            if (GameObject.Find("DeltaSpawn_1") == null)
            {
                var sp1 = new GameObject("DeltaSpawn_1");
                SceneManager.MoveGameObjectToScene(sp1, scene);
                sp1.transform.position = new Vector3(8, 1, 8);
                var bsp1 = sp1.AddComponent<bl_SpawnPoint>();
                bsp1.m_Team = (global::Team)1;
                Debug.Log("CREATED: DeltaSpawn_1 (Team1)");
            }
            if (GameObject.Find("DeltaSpawn_2") == null)
            {
                var sp2 = new GameObject("DeltaSpawn_2");
                SceneManager.MoveGameObjectToScene(sp2, scene);
                sp2.transform.position = new Vector3(-8, 1, -8);
                var bsp2 = sp2.AddComponent<bl_SpawnPoint>();
                bsp2.m_Team = (global::Team)2;
                Debug.Log("CREATED: DeltaSpawn_2 (Team2)");
            }
            if (GameObject.Find("DeltaSpawn_3") == null)
            {
                var sp3 = new GameObject("DeltaSpawn_3");
                SceneManager.MoveGameObjectToScene(sp3, scene);
                sp3.transform.position = new Vector3(0, 1, -12);
                var bsp3 = sp3.AddComponent<bl_SpawnPoint>();
                bsp3.m_Team = (global::Team)2;
                Debug.Log("CREATED: DeltaSpawn_3 (Team2)");
            }

            // Add KillZone if it doesn't exist
            if (GameObject.Find("KillZone") == null)
            {
                string kzPath = "Assets/MFPS/Content/Prefabs/GamePlay/Level/KillZone.prefab";
                var kzPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(kzPath);
                if (kzPrefab != null)
                {
                    var kz = PrefabUtility.InstantiatePrefab(kzPrefab, scene) as GameObject;
                    kz.transform.position = new Vector3(0, -5, 0);
                    kz.transform.localScale = new Vector3(200, 1, 200);
                    Debug.Log("INSTANTIATED: KillZone");
                }
                else
                {
                    Debug.LogError("KillZone prefab not found: " + kzPath);
                }
            }

            // NavMesh bake skipped for now - will add later if bots need it
            Debug.Log("NAV MESH BAKE SKIPPED (non-fatal)");

            // Save scene
            string savePath = "Assets/MFPS/Scenes/HeistLevel.unity";
            EditorSceneManager.SaveScene(scene, savePath);
            Debug.Log("HEIST_SCENE_SAVED: " + savePath);

            // Set build scene list
            var scenes = new System.Collections.Generic.List<EditorBuildSettingsScene>();
            scenes.Add(new EditorBuildSettingsScene(savePath, true));
            EditorBuildSettings.scenes = scenes.ToArray();
            Debug.Log("BUILD_SCENES_SET");
        }
    }
}