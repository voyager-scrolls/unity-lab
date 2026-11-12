using UnityEngine;
using UnityEngine.UI;

public static class GameSprites {
    public static Sprite White;
    public static Sprite Get() {
        if (White == null) {
            var tex = new Texture2D(4, 4, TextureFormat.RGBA32, false);
            var cols = new Color32[16];
            for (int i = 0; i < 16; i++) cols[i] = new Color32(255, 255, 255, 255);
            tex.SetPixels32(cols);
            tex.Apply();
            White = Sprite.Create(tex, new Rect(0f, 0f, 4f, 4f), new Vector2(0.5f, 0.5f), 4f);
            White.name = "WhiteSquare";
        }
        return White;
    }
}

public static class ContraBoot {
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Boot() {
        var stale = GameObject.Find("Cube");
        if (stale != null) Object.Destroy(stale);
        if (GameObject.Find("ContraGame") != null) return;
        new GameObject("ContraGame");

        var camGo = new GameObject("MainCamera");
        var cam = camGo.AddComponent<Camera>();
        cam.tag = "MainCamera";
        cam.orthographic = true;
        cam.orthographicSize = 6f;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.08f, 0.09f, 0.16f);
        camGo.transform.position = new Vector3(0f, 1f, -10f);
        var fc = camGo.AddComponent<FollowCam>();
        fc.minX = -26f; fc.maxX = 26f;

        MakeBox("Ground", new Vector3(0f, -3.5f, 0f), new Vector3(80f, 1f, 1f), new Color(0.34f, 0.36f, 0.40f));
        MakeBox("WallL", new Vector3(-40f, 1f, 0f), new Vector3(1f, 14f, 1f), new Color(0f, 0f, 0f, 0f));
        MakeBox("WallR", new Vector3(40f, 1f, 0f), new Vector3(1f, 14f, 1f), new Color(0f, 0f, 0f, 0f));

        MakePlatform("Plat1", new Vector3(-18f, -1.0f, 0f), new Vector3(7f, 0.4f, 1f));
        MakePlatform("Plat2", new Vector3(-7f, 0.8f, 0f), new Vector3(7f, 0.4f, 1f));
        MakePlatform("Plat3", new Vector3(5f, -1.0f, 0f), new Vector3(7f, 0.4f, 1f));
        MakePlatform("Plat4", new Vector3(17f, 0.8f, 0f), new Vector3(7f, 0.4f, 1f));
        MakePlatform("Plat5", new Vector3(26f, 2.4f, 0f), new Vector3(7f, 0.4f, 1f));

        var p = new GameObject("Player");
        p.transform.position = new Vector3(0f, -1.9f, 0f);
        var psr = p.AddComponent<SpriteRenderer>();
        psr.sprite = GameSprites.Get();
        psr.color = new Color(0.25f, 0.55f, 1f);
        p.transform.localScale = new Vector3(1f, 2f, 1f);
        p.AddComponent<BoxCollider2D>();
        p.AddComponent<Rigidbody2D>();
        p.AddComponent<ContraPlayer>();
        fc.target = p.transform;

        MakeHint();
        Debug.Log("CONTRA_BOOTED");
    }

    static void MakeBox(string name, Vector3 pos, Vector3 size, Color color) {
        var go = new GameObject(name);
        go.transform.position = pos;
        go.transform.localScale = size;
        if (color.a > 0f) {
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = GameSprites.Get();
            sr.color = color;
        }
        go.AddComponent<BoxCollider2D>();
    }

    static void MakePlatform(string name, Vector3 pos, Vector3 size) {
        var go = new GameObject(name);
        go.transform.position = pos;
        go.transform.localScale = size;
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = GameSprites.Get();
        sr.color = new Color(0.2f, 0.75f, 0.3f);
        go.AddComponent<BoxCollider2D>();
        var eff = go.AddComponent<PlatformEffector2D>();
        eff.useOneWay = true;
    }

    static void MakeHint() {
        var canvasGo = new GameObject("HintCanvas");
        var canvas = canvasGo.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        var txt = canvasGo.AddComponent<Text>();
        txt.color = new Color(1f, 1f, 1f, 0.85f);
        txt.fontSize = 18;
        txt.alignment = TextAnchor.LowerLeft;
        txt.text = "A/D move   Space jump   W/S aim   Shift = aim lock   Z fire   S+Space drop";
        Font f = null;
        try { f = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); } catch (System.Exception) {}
        if (f == null) { try { f = Resources.GetBuiltinResource<Font>("Arial.ttf"); } catch (System.Exception) {} }
        txt.font = f;
        var rt = txt.rectTransform;
        rt.anchorMin = new Vector2(0f, 0f);
        rt.anchorMax = new Vector2(1f, 0f);
        rt.offsetMin = new Vector2(12f, 8f);
        rt.offsetMax = new Vector2(-12f, 44f);
    }
}
