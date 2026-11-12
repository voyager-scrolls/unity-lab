using UnityEngine;

public class ContraSpawner : MonoBehaviour {
    public float interval = 2.5f;
    public int maxAlive = 6;
    public int maxJumpers = 2;
    float timer;
    bool cap1;
    bool cap2;

    // Zone choreography along the march: teach -> ambush -> breath -> pressure -> crossfire -> gauntlet
    static readonly float[] ZMin = { -60f, -30f, -12f, -8f, 4f, 24f };
    static readonly float[] ZMax = { -30f, -12f, -8f, 4f, 24f, 54f };
    static readonly float[] ZInt = { 3.5f, 2.8f, 2.2f, 2.2f, 2.6f, 1.9f };
    static readonly float[] ZJump = { 0f, 0.35f, 0.4f, 0.4f, 0.25f, 0.4f };

    void Update() {
        if (ContraState.gameOver) return;
        var ps = Object.FindObjectsByType<ContraPlayer>(FindObjectsSortMode.None);
        if (ps.Length == 0) return;
        float px = ps[0].transform.position.x;

        if (!cap1 && px > 0f) { cap1 = true; SpawnCapsule(px + 12f); }
        if (!cap2 && px > 34f) { cap2 = true; SpawnCapsule(px + 12f); }

        timer -= Time.deltaTime;
        if (timer > 0f) return;

        // breath windows: the march stands down before each water crossing
        if ((px > -15f && px < -5f) || (px > 17f && px < 27f)) { timer = 0.4f; return; }

        int z = 0;
        for (int i = 0; i < ZMin.Length; i++) {
            if (px >= ZMin[i] && px < ZMax[i]) { z = i; break; }
        }
        timer = ZInt[z];

        var cam = Camera.main;
        if (cam == null) return;
        var rootT = GameObject.Find("ContraGame");
        if (rootT == null) return;
        float x = Mathf.Clamp(cam.transform.position.x + 11.5f, -58f, 55f);
        var hit = Physics2D.Raycast(new Vector2(x, 0f), Vector2.down, 8f);
        if (hit.collider == null) return; // water gap ahead: no ground to land on, skip

        int jumpers = Object.FindObjectsByType<ContraJumper>(FindObjectsSortMode.None).Length;
        int runners = Object.FindObjectsByType<ContraEnemy>(FindObjectsSortMode.None).Length;

        if (jumpers < maxJumpers && Random.value < ZJump[z]) {
            var jgo = new GameObject("Jumper");
            jgo.transform.position = new Vector3(x, -2.4f, 0f);
            var jsr = jgo.AddComponent<SpriteRenderer>();
            jsr.sprite = GameSprites.Get();
            jsr.color = new Color(0.95f, 0.45f, 0.15f);
            jgo.transform.localScale = new Vector3(0.9f, 1.2f, 1f);
            var jbc = jgo.AddComponent<BoxCollider2D>();
            jbc.sharedMaterial = new PhysicsMaterial2D("jumperSlip") { friction = 0f, bounciness = 0f };
            jgo.AddComponent<Rigidbody2D>();
            jgo.transform.SetParent(rootT.transform, true);
            jgo.AddComponent<ContraJumper>();
        } else if (runners < maxAlive) {
            var go = new GameObject("Runner");
            go.transform.position = new Vector3(x, -2.4f, 0f);
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = GameSprites.Get();
            sr.color = new Color(0.85f, 0.2f, 0.2f);
            go.transform.localScale = new Vector3(0.9f, 1.2f, 1f);
            var bc = go.AddComponent<BoxCollider2D>();
            bc.sharedMaterial = new PhysicsMaterial2D("enemySlip") { friction = 0f, bounciness = 0f };
            go.AddComponent<Rigidbody2D>();
            go.transform.SetParent(rootT.transform, true);
            go.AddComponent<ContraEnemy>();
        }
    }

    void SpawnCapsule(float x) {
        var rootT = GameObject.Find("ContraGame");
        if (rootT == null) return;
        var go = new GameObject("Capsule");
        go.transform.position = new Vector3(x, -1.1f, 0f);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = GameSprites.Get();
        sr.color = new Color(1f, 0.5f, 0.1f);
        var bc = go.AddComponent<BoxCollider2D>();
        bc.isTrigger = true;
        go.transform.SetParent(rootT.transform, true);
        go.AddComponent<ContraCapsule>();
    }
}
