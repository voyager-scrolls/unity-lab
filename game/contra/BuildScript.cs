using System.IO; using System.Linq; using UnityEngine; using UnityEditor; using UnityEditor.SceneManagement;
public static class BuildScript {
    [MenuItem("Build/Perform")]
    public static void PerformBuild() {
        var scenes = new string[] { "Assets/Scenes/Sample.unity" };
        if (!File.Exists(scenes[0])) {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            System.IO.Directory.CreateDirectory("Assets/Scenes");
            EditorSceneManager.SaveScene(scene, scenes[0]);
            Debug.Log("SCENE_CREATED_BY_SCRIPT");
        }
        EditorBuildSettings.scenes = scenes.Select(s => new EditorBuildSettingsScene(s, true)).ToArray();
        AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
        AssetDatabase.SaveAssets();
        if (!File.Exists(scenes[0])) throw new System.Exception("SCENE_SAVE_FAILED: " + scenes[0]);
        var target = BuildTarget.WebGL; var outDir = "Builds/WebGL/probe";
        if (target == BuildTarget.WebGL) PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Disabled;
        var report = BuildPipeline.BuildPlayer(scenes, outDir, target, BuildOptions.None);
        if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new System.Exception("BUILD_FAILED: " + report.summary.result);
        Debug.Log("BUILD_OK " + report.summary.totalSize + " bytes");
    }
}
