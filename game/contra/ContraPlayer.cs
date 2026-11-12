using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

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
    Collider2D groundCol;
    bool dropping;
    float dropTimer;
    Collider2D dropCol;
    public float dropDuration = 0.25f;
    bool dead;
    bool won;

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
        barrel.SetParent(transform.parent, true);
        barrel.position = transform.position;
    }

    void Update() {
        if (dead || won) return;
        if (transform.position.y < -3f) { Die(); return; } // fell into water
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
        if (dropping) grounded = false;
        bool dropWish = grounded && Input.GetKey(KeyCode.S) && Input.GetKeyDown(KeyCode.Space);
        if (dropWish && groundCol != null && groundCol.GetComponent<PlatformEffector2D>() != null && !dropping) {
            dropping = true;
            dropTimer = dropDuration;
            dropCol = groundCol;
            Physics2D.IgnoreCollision(col, dropCol, true);
            rb.linearVelocity = new Vector2(rb.linearVelocity.x, -2f);
        } else if (Input.GetKeyDown(KeyCode.Space) && grounded) {
            rb.linearVelocity = new Vector2(rb.linearVelocity.x, jumpSpeed);
        }
        if (dropping) {
            dropTimer -= Time.deltaTime;
            if (dropTimer <= 0f) {
                if (dropCol != null) Physics2D.IgnoreCollision(col, dropCol, false);
                dropCol = null;
                dropping = false;
            }
        }

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

    void OnCollisionEnter2D(Collision2D c) {
        if (dead || won) return;
        if (c.collider != null && c.collider.GetComponent<ContraEnemy>() != null) Die();
    }

    void OnTriggerEnter2D(Collider2D other) {
        if (dead || won) return;
        if (other != null && other.CompareTag("Finish")) Win();
    }

    void Win() {
        won = true;
        rb.linearVelocity = Vector2.zero;
        var sr = GetComponent<SpriteRenderer>();
        if (sr != null) sr.color = new Color(1f, 0.85f, 0.3f); // gold
        var hint = GameObject.Find("HintCanvas");
        if (hint != null) {
            var t = hint.GetComponent<Text>();
            if (t != null) t.text = "STAGE CLEAR - you reached the gate";
        }
        var sp = GameObject.Find("Spawner");
        if (sp != null) sp.SetActive(false);
    }

    void Die() {
        dead = true;
        var sr = GetComponent<SpriteRenderer>();
        if (sr != null) sr.color = new Color(0.9f, 0.15f, 0.15f);
        if (barrel != null) barrel.gameObject.SetActive(false);
        ContraRestarter.Schedule(0.6f);
    }

    bool CheckGrounded() {
        groundCol = null;
        Vector2 p = transform.position;
        var hits = Physics2D.OverlapBoxAll(p + Vector2.down * 1.05f, new Vector2(0.7f, 0.16f), 0f);
        foreach (var c in hits) {
            if (c == col || c.isTrigger) continue;
            groundCol = c;
            return true;
        }
        return false;
    }

    void Fire() {
        var b = new GameObject("Bullet");
        b.transform.position = barrel.position + (Vector3)(aimDir * 0.25f);
        b.transform.SetParent(transform.parent, true);
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
