using UnityEngine;

// Stationary wall turret: fires straight horizontal shots at standing-chest height,
// so lying prone lets them pass overhead. Three hits to kill.
public class ContraTurret : MonoBehaviour {
    public int hp = 3;
    public float interval = 1.7f;
    public float fireSpeed = 6f;
    public float facing = -1f;
    float timer = 1f;

    void Update() {
        timer -= Time.deltaTime;
        if (timer > 0f) return;
        timer = interval;

        var cam = Camera.main;
        if (cam != null) {
            float halfW = cam.orthographicSize * cam.aspect;
            if (transform.position.x > cam.transform.position.x + halfW) return; // do not fire from offscreen
        }

        var b = new GameObject("EnemyBullet");
        b.transform.position = transform.position + new Vector3(facing * 0.7f, 0.9f, 0f);
        b.transform.SetParent(transform.parent, true);
        b.transform.localScale = new Vector3(0.35f, 0.16f, 1f);
        var sr = b.AddComponent<SpriteRenderer>();
        sr.sprite = GameSprites.Get();
        sr.color = new Color(1f, 0.45f, 0.1f);
        var bc = b.AddComponent<BoxCollider2D>();
        bc.isTrigger = true;
        var brb = b.AddComponent<Rigidbody2D>();
        brb.gravityScale = 0f;
        brb.linearVelocity = new Vector2(facing * fireSpeed, 0f);
        var bl = b.AddComponent<Bullet2D>();
        bl.enemyBullet = true;
    }

    public void Hit() {
        hp--;
        var sr = GetComponent<SpriteRenderer>();
        if (hp <= 0) {
            ContraState.score += 500;
            if (sr != null) sr.color = Color.white;
            Destroy(gameObject, 0.08f);
        } else if (sr != null) {
            sr.color = new Color(1f, 0.45f, 0.35f);
        }
    }
}
