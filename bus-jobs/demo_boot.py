import subprocess, os, glob, json, time
# --- sync project from Drive (or scaffold a demo one) ---
cfg = json.load(open('/content/unitylab_config.json'))
UNITY = open('/content/unity_bin.txt').read().strip()
WORK = '/content/work'
t0 = time.time()
os.makedirs(WORK, exist_ok=True)
proj_candidates = sorted(glob.glob(cfg['DRIVE_PROJECTS'] + '/*/Assets')) if os.path.isdir(cfg['DRIVE_PROJECTS']) else []
if cfg['SYNC_PROJECT'] and proj_candidates:
    src_assets_parent = os.path.dirname(proj_candidates[0])
    name = os.path.basename(src_assets_parent)
    DST = os.path.join(WORK, name)
    r = subprocess.run(['bash', '-lc', 'mkdir -p "%s" && cp -a "%s/." "%s/"' % (WORK, src_assets_parent, DST)],
                       capture_output=True, text=True)
    print('synced project:', name, 'rc:', r.returncode, '(Drive-mount copies are slow for big assets)')
    if r.returncode != 0: print((r.stderr or '')[-1200:])
    assert r.returncode == 0, 'project copy failed'
else:
    name = 'demo'
    DST = os.path.join(WORK, 'demo')
    if not os.path.isdir(DST + '/Assets'):
        r = subprocess.run(['bash', '-lc', '"%s" -batchmode -quit -nographics -createProject "%s" -logFile /content/create.log; echo EXIT_CODE=$?' % (UNITY, DST)],
                           capture_output=True, text=True, timeout=1800)
        okc = [l for l in (r.stdout or '').splitlines() if l.startswith('EXIT_CODE=')]
        logtxt = open('/content/create.log', errors='ignore').read()[-2000:] if os.path.exists('/content/create.log') else '(no create.log — editor never started)'
        print('demo project created:', okc, '| %.1f min' % ((time.time() - t0) / 60))
        assert os.path.isdir(DST + '/Assets'), 'demo create failed: ' + logtxt
os.makedirs(os.path.join(DST, 'Assets', 'Editor'), exist_ok=True)
with open(os.path.join(DST, 'Assets', 'Editor', 'BuildScript.cs'), 'w') as f:
    f.write('''using System.IO; using System.Linq; using UnityEditor; using UnityEditor.SceneManagement; using UnityEngine;
public static class BuildScript {
    [MenuItem("Build/Perform")]
    public static void PerformBuild() {
        var scenes = new string[] { "Assets/Scenes/Sample.unity" };
        if (!File.Exists("Assets/Scenes/Sample.unity")) {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
            GameObject.CreatePrimitive(PrimitiveType.Cube);
            System.IO.Directory.CreateDirectory("Assets/Scenes");
            EditorSceneManager.SaveScene(scene, scenes[0]);
            Debug.Log("SCENE_CREATED_BY_SCRIPT");
        }
        EditorBuildSettings.scenes = scenes.Select(s => new EditorBuildSettingsScene(s, true)).ToArray();
        AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
        AssetDatabase.SaveAssets();
        if (!File.Exists(scenes[0])) throw new System.Exception("SCENE_SAVE_FAILED: " + scenes[0]);
        var demoDir = "Assets/Demo";
        if (System.IO.Directory.Exists(demoDir)) {
            var refDir = demoDir + "/MatRefs";
            if (!System.IO.Directory.Exists(refDir)) System.IO.Directory.CreateDirectory(refDir);
            var refMatPath = refDir + "/unlit_ref.mat";
            if (!File.Exists(refMatPath)) AssetDatabase.CreateAsset(new Material(Shader.Find("Unlit/Color")), refMatPath);
        }
        var target = BuildTarget.WebGL; var outDir = "Builds/WebGL/probe";
        if (target == BuildTarget.WebGL) PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Disabled;
        var report = BuildPipeline.BuildPlayer(scenes, outDir, target, BuildOptions.None);
        if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new System.Exception("BUILD_FAILED: " + report.summary.result);
        Debug.Log("BUILD_OK " + report.summary.totalSize + " bytes");
    }
}
''')
DEMO_DIR = os.path.join(DST, 'Assets', 'Demo')
if name == 'demo':
    os.makedirs(DEMO_DIR, exist_ok=True)
    GAME_BOOT_CS = '''using UnityEngine;
public static class DemoBoot {
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Boot() {
        var stale = GameObject.Find("Cube");
        if (stale != null) Object.Destroy(stale);
        if (GameObject.Find("CubeDodger") != null) return;
        new GameObject("CubeDodger").AddComponent<GameManager>();
        Debug.Log("GAME_BOOTED");
    }
}
'''
    open(os.path.join(DEMO_DIR, 'DemoBoot.cs'), 'w').write(GAME_BOOT_CS)
    GAME_MANAGER_CS = '''
using UnityEngine;
using System.Collections.Generic;

public class GameManager : MonoBehaviour {
    public static GameManager Instance { get; private set; }
    Transform ptx; Vector3 p0, cam0;
    List<GameObject> cubes = new List<GameObject>();
    List<float> spins = new List<float>();
    GameObject dashAnchor; float dashZ;
    float spawnT = 0.8f, speed = 7f, score, best, flashT, deadT;
    bool alive = true, audioReady;
    AudioClip thud, tick;

    Material Unlit(Color c) {
        var m = new Material(Shader.Find("Unlit/Color"));
        m.color = c;
        return m;
    }

    void Start() {
        Instance = this;
        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.name = "Ground";
        ground.transform.localScale = new Vector3(6f, 1f, 60f);
        ground.GetComponent<Renderer>().material = Unlit(new Color(0.16f, 0.18f, 0.22f));
        dashAnchor = new GameObject("Dashes");
        for (float z = 0f; z < 120f; z += 4f) Dash(z);
        var cap = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        cap.name = "Player";
        cap.GetComponent<Renderer>().material = Unlit(new Color(0.95f, 0.85f, 0.2f));
        p0 = new Vector3(0f, 1f, 0f);
        ptx = cap.transform;
        ptx.position = p0;
        cam0 = new Vector3(0f, 7.5f, p0.z - 10f);
        thud = MakeBeep(110f, 0.30f);
        tick = MakeBeep(300f, 0.06f);
        Debug.Log("GAME_READY");
    }

    void Dash(float z) {
        for (int k = -1; k <= 1; k += 2) {
            var d = GameObject.CreatePrimitive(PrimitiveType.Cube);
            d.name = "Dash";
            d.transform.SetParent(dashAnchor.transform, false);
            d.transform.localScale = new Vector3(0.25f, 0.05f, 1.6f);
            d.transform.position = new Vector3(4.5f * k, 0.05f, z);
            d.GetComponent<Renderer>().material = Unlit(new Color(0.35f, 0.38f, 0.45f));
        }
    }

    void Update() {
        if (flashT > 0f) flashT = Mathf.Max(0f, flashT - Time.deltaTime * 2f);
        if (!alive) {
            deadT += Time.deltaTime;
            if (deadT > 0.6f && (Input.anyKeyDown || Input.GetMouseButtonDown(0))) Restart();
            return;
        }
        speed = 7f + score * 0.05f;
        Vector3 pos = ptx.position;
        pos.z += speed * Time.deltaTime;
        float mv = Input.GetAxisRaw("Horizontal");
        if (Input.touchCount > 0 && Input.GetTouch(0).phase == TouchPhase.Began)
            mv = (Input.GetTouch(0).position.x >= Screen.width / 2) ? 1f : -1f;
        else if (Input.GetMouseButtonDown(0))
            mv = (Input.mousePosition.x >= Screen.width / 2) ? 1f : -1f;
        if (!audioReady && Mathf.Abs(mv) > 0.1f) {
            audioReady = true;
            if (tick != null) AudioSource.PlayClipAtPoint(tick, pos);
        }
        pos.x = Mathf.Clamp(pos.x + mv * 9f * Time.deltaTime, -9f, 9f);
        ptx.position = pos;
        score = pos.z;
        while (dashZ < pos.z + 120f) { Dash(dashZ); dashZ += 4f; }
        spawnT -= Time.deltaTime;
        if (spawnT <= 0) { spawnT = Mathf.Max(0.3f, 1.1f - score * 0.004f); Spawn(pos.z); }
        float fall = 4.5f + score * 0.01f;
        for (int i = cubes.Count - 1; i >= 0; i--) {
            var t = cubes[i].transform;
            float s = t.localScale.x;
            t.position += Vector3.down * fall * Time.deltaTime;
            t.Rotate(0f, spins[i] * Time.deltaTime, spins[i] * 0.6f * Time.deltaTime);
            if (t.position.y < -3f || t.position.z < pos.z - 12f) { Destroy(cubes[i]); cubes.RemoveAt(i); spins.RemoveAt(i); continue; }
            bool overlap = Mathf.Abs(t.position.x - pos.x) < 0.5f + 0.5f * s
                        && Mathf.Abs(t.position.z - pos.z) < 0.5f + 0.5f * s
                        && (t.position.y - 0.5f * s) < 2.0f && (t.position.y + 0.5f * s) > 0.0f;
            if (overlap) Die();
        }
        var cam = Camera.main.transform;
        cam.position = new Vector3(pos.x * 0.25f, 7.5f + speed * 0.02f, pos.z - 10f);
        cam.LookAt(pos + Vector3.forward * 6f);
    }

    void Spawn(float z) {
        var g = GameObject.CreatePrimitive(PrimitiveType.Cube);
        g.name = "Hazard";
        float s = Random.Range(1.0f, 1.6f);
        g.transform.localScale = new Vector3(s, s, s);
        float x = Random.Range(-9f, 9f);
        if (Random.value < 0.75f) {
            float lead = Mathf.Max(1.6f, 6f - score * 0.05f);
            float aim = ptx.position.x + Random.Range(-lead, lead);
            if (Mathf.Abs(aim - ptx.position.x) < 1.1f)
                aim = ptx.position.x + Mathf.Sign(aim - ptx.position.x + 0.001f) * 1.6f;
            x = Mathf.Clamp(aim, -9f, 9f);
        }
        g.transform.position = new Vector3(x, 13f, z + Random.Range(40f, 60f));
        g.GetComponent<Renderer>().material = Unlit(Random.value < 0.75f
            ? new Color(0.85f, 0.12f, 0.10f)
            : new Color(0.15f, 0.55f, 0.95f));
        cubes.Add(g);
        spins.Add(Random.Range(40f, 140f) * (Random.value < 0.5f ? 1f : -1f));
    }

    void Die() {
        if (!alive) return;
        alive = false; deadT = 0f; flashT = 1f;
        best = Mathf.Max(best, score);
        if (thud != null) AudioSource.PlayClipAtPoint(thud, new Vector3(0f, 2f, 0f));
        Debug.Log("GAME_DIED " + score.ToString("0") + "m");
    }

    void Restart() {
        alive = true; score = 0; spawnT = 0.8f; speed = 7f;
        foreach (var c in cubes) Destroy(c);
        cubes.Clear(); spins.Clear();
        ptx.position = p0;
        Camera.main.transform.position = cam0;
        Debug.Log("GAME_RESTART");
    }

    void OnGUI() {
        if (flashT > 0f) {
            GUI.color = new Color(1f, 0.1f, 0f, flashT * 0.55f);
            GUI.DrawTexture(new Rect(0, 0, Screen.width, Screen.height), Texture2D.whiteTexture);
            GUI.color = Color.white;
        }
        if (alive) {
            GUIStyle hud = new GUIStyle(GUI.skin.label) { fontSize = 20 };
            GUI.Label(new Rect(10, 8, 460, 32), "Distance: " + score.ToString("0") + " m" + (best > 0 ? "   Best: " + best.ToString("0") : ""), hud);
            if (score < 12f) {
                GUIStyle tip = new GUIStyle(GUI.skin.label) { fontSize = 14 };
                GUI.Label(new Rect(10, 40, 460, 24), "A/D or arrows dodge cubes; tap left/right half on touch", tip);
            }
        } else {
            GUI.Box(new Rect(Screen.width / 2 - 210, Screen.height / 2 - 90, 420, 180), "");
            var st = new GUIStyle(GUI.skin.label) { alignment = TextAnchor.MiddleCenter, wordWrap = true, fontSize = 18 };
            float left = Screen.width / 2 - 190, midY = Screen.height / 2;
            GUI.Label(new Rect(left, midY - 70, 380, 30), "GAME OVER", st);
            GUI.Label(new Rect(left, midY - 40, 380, 26), "Distance: " + score.ToString("0") + " m", st);
            GUI.Label(new Rect(left, midY - 14, 380, 26), "Best: " + best.ToString("0") + " m", st);
            GUI.Label(new Rect(left, midY + 14, 380, 26), deadT < 0.6f ? "..." : "Click, tap or press any key to restart", st);
        }
    }

    AudioClip MakeBeep(float freq, float dur) {
        int f = 44100, n = (int)(f * dur);
        var d = new float[n];
        for (int i = 0; i < n; i++) {
            float env = 1f - (float)i / n;
            d[i] = 0.5f * Mathf.Cos(6.28318f * freq * i / f) * env * env;
        }
        var clip = AudioClip.Create("beep", n, 1, f, false);
        clip.SetData(d, 0);
        return clip;
    }
}
'''
    open(os.path.join(DEMO_DIR, 'GameManager.cs'), 'w').write(GAME_MANAGER_CS)
    print('DEMO GAME WRITTEN: DemoBoot.cs + GameManager.cs ->', DEMO_DIR)
open('/content/work_project.txt', 'w').write(DST)
open('/content/work_name.txt', 'w').write(name)
print('GATE 3 PASS — project ready at', DST)
