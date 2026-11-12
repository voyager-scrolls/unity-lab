using UnityEngine;

public class ContraPlayer : MonoBehaviour {
    public float runSpeed = 7f;
    public float jumpSpeed = 13f;
    public float bulletSpeed = 14f;
    public float fireCooldown = 0.16f;
    public float barrelDist = 0.75f;

    Rigidbody2D rb;
    Collider2D col;
    Transform barrel;
    float fireTimer;
    float faceDir = 1f;
    Vector2 aimDir = Vector2.right;
    bool grounded;

    void Awake() {
        rb = GetComponent<Rigidbody2D>();
        col = GetComponent<Collider2D>();
        rb.gravityScale = 4f;
        rb.freezeRotation = true;
        var b = new GameObject("Barrel");
        var sr = b.AddComponent<SpriteRenderer>();
        sr.sprite = GameSprites.Get();
        sr.color = Color.yellow;
        b.transform.localScale = new Vector3(0.45f, 0.18f, 1f);
        barrel = b.transform;
        barrel.position = transform.position;
    }

    void Update() {
        float h = Input.GetAxisRaw("Horizontal");
        float v = Input.GetAxisRaw("Vertical");
        bool locked = Input.GetKey(KeyCode.LeftShift);

        if (h != 0f) faceDir = Mathf.Sign(h);
        if (locked) {
            rb.linearVelocity = new Vector2(0f, rb.linearVelocity.y);
        } else {
            rb.linearVelocity = new Vector2(h * runSpeed, rb.linearVelocity.y);
        }

        grounded = CheckGrounded();
        if (Input.GetKeyDown(KeyCode.Space) && grounded)
            rb.linearVelocity = new Vector2(rb.linearVelocity.x, jumpSpeed);

        Vector2 a = new Vector2(h, v);
        if (a.sqrMagnitude < 0.01f) a = new Vector2(faceDir, 0f);
        if (grounded && !locked && v < 0f && h == 0f) a = new Vector2(faceDir, 0f);
        aimDir = a.normalized;

        float ang = Mathf.Atan2(aimDir.y, aimDir.x) * Mathf.Rad2Deg;
        barrel.position = transform.position + (Vector3)(aimDir * barrelDist);
        barrel.rotation = Quaternion.Euler(0f, 0f, ang);

        fireTimer -= Time.deltaTime;
        bool fireHeld = Input.GetKey(KeyCode.LeftControl) || Input.GetKey(KeyCode.Z);
        if (fireHeld && fireTimer <= 0f) {
            fireTimer = fireCooldown;
            Fire();
        }
    }

    bool CheckGrounded() {
        Vector2 p = transform.position;
        var hits = Physics2D.OverlapBoxAll(p + Vector2.down * 1.05f, new Vector2(0.7f, 0.16f), 0f);
        foreach (var c in hits) {
            if (c == col || c.isTrigger) continue;
            return true;
        }
        return false;
    }

    void Fire() {
        var b = new GameObject("Bullet");
        b.transform.position = barrel.position + (Vector3)(aimDir * 0.25f);
        var sr = b.AddComponent<SpriteRenderer>();
        sr.sprite = GameSprites.Get();
        sr.color = Color.white;
        b.transform.localScale = new Vector3(0.25f, 0.25f, 1f);
        var bc = b.AddComponent<BoxCollider2D>();
        bc.isTrigger = true;
        bc.size = Vector2.one;
        var brb = b.AddComponent<Rigidbody2D>();
        brb.gravityScale = 0f;
        brb.linearVelocity = aimDir * bulletSpeed;
        var bl = b.AddComponent<Bullet2D>();
        bl.ignore = col;
    }
}
