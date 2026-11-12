using UnityEngine;

public class ContraSpawner : MonoBehaviour {
    public float interval = 2.5f;
    public int maxAlive = 6;
    float timer;

    void Update() {
        timer -= Time.deltaTime;
        if (timer > 0f) return;
        timer = interval;
        if (Object.FindObjectsByType<ContraEnemy>(FindObjectsSortMode.None).Length >= maxAlive) return;
        var cam = Camera.main;
        if (cam == null) return;
        var rootT = GameObject.Find("ContraGame");
        if (rootT == null) return;
        float x = Mathf.Clamp(cam.transform.position.x + 11.5f, -39f, 39f); // just off the visible right edge
        var go = new GameObject("Runner");
        go.transform.position = new Vector3(x, -2.4f, 0f);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = GameSprites.Get();
        sr.color = new Color(0.85f, 0.2f, 0.2f);
        go.transform.localScale = new Vector3(0.9f, 1.2f, 1f);
        var bc = go.AddComponent<BoxCollider2D>();
        bc.sharedMaterial = new PhysicsMaterial2D("enemySlip") { friction = 0f, bounciness = 0f };
        go.transform.SetParent(rootT.transform, true);
        go.AddComponent<ContraEnemy>();
    }
}
