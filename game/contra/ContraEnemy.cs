using UnityEngine;

public class ContraEnemy : MonoBehaviour {
    public float runSpeed = 3.5f;
    Rigidbody2D rb;
    bool dying;

    void Awake() {
        rb = GetComponent<Rigidbody2D>();
        rb.gravityScale = 4f;
        rb.freezeRotation = true;
    }

    void FixedUpdate() {
        if (dying) return;
        rb.linearVelocity = new Vector2(-runSpeed, rb.linearVelocity.y);
        var cam = Camera.main;
        float limit = cam != null ? cam.transform.position.x - 13f : -38f; // despawn behind camera view
        if (transform.position.x < limit) Destroy(gameObject);
    }

    public void Die() {
        if (dying) return;
        dying = true;
        var sr = GetComponent<SpriteRenderer>();
        if (sr != null) sr.color = Color.white; // hit flash
        Destroy(gameObject, 0.08f);
    }
}
