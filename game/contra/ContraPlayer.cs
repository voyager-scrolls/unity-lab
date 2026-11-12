using UnityEngine;
using UnityEngine.UI;

public class ContraPlayer : MonoBehaviour {
    public float runSpeed = 7f;
    public float jumpSpeed = 13f;
    public float bulletSpeed = 14f;
    public float fireCooldown = 0.16f;
    public float barrelDist = 0.75f;
    public float dropDuration = 0.25f;
    public bool spread;

    Rigidbody2D rb;
    BoxCollider2D col;
    SpriteRenderer sr;
    SpriteRenderer barrelSr;
    Transform barrel;
    float fireTimer;
    float faceDir = 1f;
    Vector2 aimDir = Vector2.right;
    bool grounded;
    Collider2D groundCol;
    bool dropping;
    float dropTimer;
    Collider2D dropCol;
    bool dead;
    bool won;
    bool prone;
    Camera cam;

    void Awake() {
        rb = GetComponent<Rigidbody2D>();
        col = GetComponent<BoxCollider2D>();
        sr = GetComponent<SpriteRenderer>();
        var bodyT = transform.Find("Body");
        if (bodyT != null && bodyT.GetComponent<SpriteRenderer>() != null) sr = bodyT.GetComponent<SpriteRenderer>();
        rb.gravityScale = 4f;
        rb.freezeRotation = true;
        cam = Camera.main;
        var b = new GameObject("Barrel");
        barrelSr = b.AddComponent<SpriteRenderer>();
        barrelSr.sprite = GameSprites.Get();
        barrelSr.color = Color.yellow;
        b.transform.localScale = new Vector3(0.45f, 0.18f, 1f);
        barrel = b.transform;
        barrel.SetParent(transform.parent, true);
        barrel.position = transform.position;
        ContraSfx.Init();
    }

    void Update() {
        if (dead || won) return;
        if (cam == null) cam = Camera.main;
        if (transform.position.y < -3f) { Die(); return; } // fell into water

        float h = Input.GetAxisRaw("Horizontal");
        float v = Input.GetAxisRaw("Vertical");
        bool locked = Input.GetKey(KeyCode.LeftShift);
        if (h != 0f) faceDir = Mathf.Sign(h);

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
            SetProne(false);
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

        // prone: hold S on the ground (classic down = lie flat, bullets pass overhead)
        bool wantProne = grounded && !dropping && Input.GetKey(KeyCode.S) && v <= 0f;
        if (wantProne != prone) SetProne(wantProne);

        if (prone || locked) rb.linearVelocity = new Vector2(0f, rb.linearVelocity.y);
        else rb.linearVelocity = new Vector2(h * runSpeed, rb.linearVelocity.y);

        // no-backscroll camera: the left edge of the view is a hard wall
        if (cam != null) {
            float halfW = cam.orthographicSize * cam.aspect;
            float minX = cam.transform.position.x - halfW + 0.7f;
            if (rb.position.x < minX) rb.position = new Vector2(minX, rb.position.y);
        }

        Vector2 a;
        if (prone) {
            a = new Vector2(faceDir, 0f);
        } else {
            a = new Vector2(h, v);
            if (a.sqrMagnitude < 0.01f) a = new Vector2(faceDir, 0f);
            if (grounded && !locked && v < 0f && h == 0f) a = new Vector2(faceDir, 0f);
        }
        aimDir = a.normalized;

        float ang = Mathf.Atan2(aimDir.y, aimDir.x) * Mathf.Rad2Deg;
        float yOff = prone ? -0.5f : 0f;
        barrel.position = transform.position + new Vector3(0f, yOff, 0f) + (Vector3)(aimDir * barrelDist);
        barrel.rotation = Quaternion.Euler(0f, 0f, ang);
        barrelSr.color = spread ? new Color(1f, 0.55f, 0.1f) : Color.yellow;

        fireTimer -= Time.deltaTime;
        bool fireHeld = Input.GetKey(KeyCode.LeftControl) || Input.GetKey(KeyCode.Z);
        if (fireHeld && fireTimer <= 0f) {
            fireTimer = fireCooldown;
            Fire();
        }
    }

    void SetProne(bool p) {
        prone = p;
        // shrink the BODY and the collider, both anchored to the feet, never the root transform:
        // scaling the root around its centre made the sprite and hitbox float half a unit off the ground
        if (sr != null) {
            sr.transform.localScale = new Vector3(1f, p ? 1f : 2f, 1f);
            sr.transform.localPosition = new Vector3(0f, p ? -0.5f : 0f, 0f);
        }
        if (col != null) {
            col.size = new Vector2(1f, p ? 1f : 2f);
            col.offset = new Vector2(0f, p ? -0.5f : 0f);
        }
    }

    void OnCollisionEnter2D(Collision2D c) {
        if (dead || won) return;
        if (c.collider == null) return;
        if (c.collider.GetComponent<ContraEnemy>() != null || c.collider.GetComponent<ContraJumper>() != null) Die();
    }

    void OnTriggerEnter2D(Collider2D other) {
        if (dead || won || other == null) return;
        if (other.CompareTag("Finish")) { Win(); return; }
        var cap = other.GetComponent<ContraCapsule>();
        if (cap != null) cap.Collect();
    }

    public void Kill() { Die(); }

    void Die() {
        if (dead || won) return;
        dead = true;
        ContraState.lives--;
        if (sr != null) sr.color = new Color(0.9f, 0.15f, 0.15f);
        if (barrel != null) barrel.gameObject.SetActive(false);
        ContraSfx.PlayLow();
        if (ContraState.lives <= 0) ContraState.gameOver = true;
        else ContraRestarter.Schedule(0.75f);
    }

    void Win() {
        won = true;
        rb.linearVelocity = Vector2.zero;
        if (sr != null) sr.color = new Color(1f, 0.9f, 0.3f);
        var hint = GameObject.Find("HintCanvas");
        if (hint != null) {
            var t = hint.GetComponent<Text>();
            if (t != null) t.text = "STAGE CLEAR - you reached the gate";
        }
        var sp = GameObject.Find("Spawner");
        if (sp != null) sp.SetActive(false);
    }

    bool CheckGrounded() {
        groundCol = null;
        var b = col.bounds;
        Vector2 p = new Vector2(b.center.x, b.min.y - 0.03f);
        var hits = Physics2D.OverlapBoxAll(p, new Vector2(b.size.x * 0.75f, 0.1f), 0f);
        foreach (var c in hits) {
            if (c == col || c.isTrigger) continue;
            groundCol = c;
            return true;
        }
        return false;
    }

    void Fire() {
        ContraSfx.PlayBlip();
        if (spread) {
            for (int i = -2; i <= 2; i++) SpawnBullet(i * 12f);
        } else {
            SpawnBullet(0f);
        }
    }

    void SpawnBullet(float deg) {
        Vector2 dir = aimDir;
        if (deg != 0f) {
            float r = deg * Mathf.Deg2Rad;
            dir = new Vector2(aimDir.x * Mathf.Cos(r) - aimDir.y * Mathf.Sin(r),
                              aimDir.x * Mathf.Sin(r) + aimDir.y * Mathf.Cos(r));
        }
        var b = new GameObject("Bullet");
        b.transform.position = barrel.position + (Vector3)(dir * 0.3f);
        b.transform.SetParent(transform.parent, true);
        var bsr = b.AddComponent<SpriteRenderer>();
        bsr.sprite = GameSprites.Get();
        bsr.color = Color.white;
        b.transform.localScale = new Vector3(0.3f, 0.3f, 1f);
        var bc = b.AddComponent<BoxCollider2D>();
        bc.isTrigger = true;
        var brb = b.AddComponent<Rigidbody2D>();
        brb.gravityScale = 0f;
        brb.linearVelocity = dir * bulletSpeed;
        var bl = b.AddComponent<Bullet2D>();
        bl.ignore = col;
    }
}
