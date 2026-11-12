using UnityEngine;

// Arc-jumper: parabolic hops toward the player. Leaps up THROUGH one-way platforms
// and lands on catwalks, so it chases vertically as well as horizontally.
public class ContraJumper : MonoBehaviour {
    public float hopVx = 4.5f;
    public float hopVy = 10f;
    public float hopInterval = 1.0f;

    Rigidbody2D rb;
    Collider2D col;
    float timer;
    bool dying;

    void Awake() {
        rb = GetComponent<Rigidbody2D>();
        col = GetComponent<Collider2D>();
        if (rb != null) {
            rb.gravityScale = 4f;
            rb.freezeRotation = true;
        }
        timer = Random.Range(0.15f, 0.5f);
    }

    void FixedUpdate() {
        if (dying) return;
        if (rb == null) return;
        timer -= Time.fixedDeltaTime;

        bool onGround = false;
        if (rb.linearVelocity.y <= 0.5f && col != null) {
            var b = col.bounds;
            var hit = Physics2D.Raycast(new Vector2(b.center.x, b.min.y + 0.05f), Vector2.down, 0.25f);
            onGround = hit.collider != null && hit.collider != col;
        }

        if (onGround && timer <= 0f) {
            var ps = Object.FindObjectsByType<ContraPlayer>(FindObjectsSortMode.None);
            float dir = -1f;
            if (ps.Length > 0) dir = Mathf.Sign(ps[0].transform.position.x - transform.position.x);
            rb.linearVelocity = new Vector2(dir * hopVx, hopVy);
            timer = hopInterval + Random.Range(0f, 0.5f);
        }

        var cam = Camera.main;
        float limit = cam != null ? cam.transform.position.x - 13f : -38f;
        if (transform.position.x < limit) Destroy(gameObject);
    }

    public void Die() {
        if (dying) return;
        dying = true;
        ContraState.score += 100;
        var sr = GetComponent<SpriteRenderer>();
        if (sr != null) sr.color = Color.white;
        Destroy(gameObject, 0.08f);
    }
}
