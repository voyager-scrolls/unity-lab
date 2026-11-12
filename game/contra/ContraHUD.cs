using UnityEngine;
using UnityEngine.UI;

public static class ContraState {
    public static int lives = 3;
    public static int score = 0;
    public static bool gameOver;
}

public static class ContraSfx {
    static AudioSource src;
    static AudioClip blip;
    static AudioClip low;

    public static void Init() {
        if (src != null) return;
        var go = GameObject.Find("MainCamera");
        if (go == null) return;
        src = go.GetComponent<AudioSource>();
        if (src == null) src = go.AddComponent<AudioSource>();
        src.playOnAwake = false;
        src.volume = 0.22f;
        if (blip == null) blip = MakeClip(880f, 0.05f);
        if (low == null) low = MakeClip(160f, 0.22f);
    }

    public static void PlayBlip() { if (src != null && blip != null) src.PlayOneShot(blip); }
    public static void PlayLow() { if (src != null && low != null) src.PlayOneShot(low); }

    static AudioClip MakeClip(float freq, float dur) {
        int rate = 44100;
        int n = Mathf.Max(1, (int)(rate * dur));
        var data = new float[n];
        for (int i = 0; i < n; i++) {
            float t = (float)i / rate;
            float env = 1f - (float)i / n;
            data[i] = Mathf.Sign(Mathf.Sin(2f * Mathf.PI * freq * t)) * 0.5f * env;
        }
        var c = AudioClip.Create("sfx", n, 1, rate, false);
        c.SetData(data, 0);
        return c;
    }
}

public class ContraHUD : MonoBehaviour {
    Text hud;
    Text big;
    float introT = 2.6f;

    void Start() {
        hud = MakeText("HudText", 20, TextAnchor.UpperLeft);
        var rt = hud.rectTransform;
        rt.anchorMin = new Vector2(0f, 1f);
        rt.anchorMax = new Vector2(0f, 1f);
        rt.pivot = new Vector2(0f, 1f);
        rt.anchoredPosition = new Vector2(14f, -10f);
        rt.sizeDelta = new Vector2(560f, 40f);

        big = MakeText("BigText", 44, TextAnchor.MiddleCenter);
        var bt = big.rectTransform;
        bt.anchorMin = new Vector2(0f, 0f);
        bt.anchorMax = new Vector2(1f, 1f);
        bt.offsetMin = new Vector2(0f, 0f);
        bt.offsetMax = new Vector2(0f, 60f);
    }

    Text MakeText(string name, int size, TextAnchor anchor) {
        var go = new GameObject(name);
        go.transform.SetParent(transform, false);
        var t = go.AddComponent<Text>();
        t.fontSize = size;
        t.alignment = anchor;
        t.color = Color.white;
        t.horizontalOverflow = HorizontalWrapMode.Overflow;
        t.verticalOverflow = VerticalWrapMode.Overflow;
        Font f = null;
        try { f = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); } catch (System.Exception) {}
        if (f == null) { try { f = Resources.GetBuiltinResource<Font>("Arial.ttf"); } catch (System.Exception) {} }
        t.font = f;
        return t;
    }

    void Update() {
        if (hud != null) hud.text = "LIVES " + ContraState.lives + "     SCORE " + ContraState.score;
        if (big == null) return;

        if (ContraState.gameOver) {
            big.color = Color.white;
            big.text = "GAME OVER - press R";
            if (Input.GetKeyDown(KeyCode.R)) {
                ContraState.lives = 3;
                ContraState.score = 0;
                ContraState.gameOver = false;
                ContraRestarter.Schedule(0.05f);
            }
            return;
        }

        if (introT > 0f) {
            introT -= Time.deltaTime;
            big.text = "STAGE 1  JUNGLE";
            big.color = new Color(1f, 1f, 1f, Mathf.Clamp01(introT));
        } else if (big.text.Length > 0) {
            big.text = "";
        }
    }
}
