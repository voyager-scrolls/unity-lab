using System.Collections;
using UnityEngine;
using UnityEngine.SceneManagement;

// PerfTune: forces a low-end-friendly profile at runtime so MFPS is playable
// on integrated GPUs (Intel HD 620) and 2-core laptops. Applies before the
// scene loads, then kills post-processing layers once objects exist.
public static class PerfTune
{
    static bool s_applied;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
    static void Apply()
    {
        if (s_applied) return;
        s_applied = true;

        Debug.Log("PERF_BEFORE quality=" + QualitySettings.GetQualityLevel()
            + "/" + (QualitySettings.names.Length - 1)
            + " shadows=" + QualitySettings.shadows
            + " shadowDist=" + QualitySettings.shadowDistance
            + " pixelLights=" + QualitySettings.pixelLightCount
            + " aa=" + QualitySettings.antiAliasing
            + " vSync=" + QualitySettings.vSyncCount
            + " screen=" + Screen.width + "x" + Screen.height
            + " fullscreen=" + Screen.fullScreen);

        int low = 0;
        QualitySettings.SetQualityLevel(low, true);

        QualitySettings.shadows = ShadowQuality.HardOnly;
        QualitySettings.shadowDistance = 22f;
        QualitySettings.shadowCascades = 1;
        QualitySettings.shadowResolution = ShadowResolution.Low;
        QualitySettings.pixelLightCount = 1;
        QualitySettings.antiAliasing = 0;
        QualitySettings.anisotropicFiltering = AnisotropicFiltering.Disable;
        QualitySettings.softParticles = false;
        QualitySettings.softVegetation = false;
        QualitySettings.realtimeReflectionProbes = false;
        QualitySettings.billboardsFaceCameraPosition = false;
        QualitySettings.lodBias = 0.7f;
        QualitySettings.globalTextureMipmapLimit = 1;
        QualitySettings.vSyncCount = 1;
        Application.targetFrameRate = 30;

        Debug.Log("PERF_AFTER quality=" + QualitySettings.GetQualityLevel()
            + " shadows=" + QualitySettings.shadows
            + " shadowDist=" + QualitySettings.shadowDistance
            + " pixelLights=" + QualitySettings.pixelLightCount
            + " aa=" + QualitySettings.antiAliasing
            + " texLimit=" + QualitySettings.globalTextureMipmapLimit
            + " targetFps=" + Application.targetFrameRate);
    }

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void AfterScene()
    {
        Screen.SetResolution(1280, 720, FullScreenMode.Windowed);

        int disabled = 0;
        MonoBehaviour[] all = Object.FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None);
        for (int i = 0; i < all.Length; i++)
        {
            MonoBehaviour mb = all[i];
            if (mb == null) continue;
            string tn = mb.GetType().Name;
            if (tn == "PostProcessLayer" || tn == "PostProcessVolume")
            {
                mb.enabled = false;
                disabled++;
            }
        }
        Debug.Log("PERF_POSTPROCESSING_DISABLED=" + disabled);

        GameObject go = new GameObject("PerfHud");
        Object.DontDestroyOnLoad(go);
        go.AddComponent<PerfHud>();
    }
}

// Lightweight on-screen FPS readout so playtest reports carry a number.
public class PerfHud : MonoBehaviour
{
    float acc;
    int frames;
    float fps;
    float logTimer;
    bool logged;

    void Update()
    {
        acc += Time.unscaledDeltaTime;
        frames++;
        if (acc >= 0.5f)
        {
            fps = frames / acc;
            acc = 0f;
            frames = 0;
        }

        logTimer += Time.unscaledDeltaTime;
        if (!logged && logTimer > 20f)
        {
            logged = true;
            Debug.Log("PERF_FPS_SAMPLE=" + Mathf.RoundToInt(fps));
        }
    }

    void OnGUI()
    {
        GUI.Label(new Rect(12f, 10f, 260f, 26f),
            "FPS " + Mathf.RoundToInt(fps) + "    " + Screen.width + "x" + Screen.height);
    }
}
