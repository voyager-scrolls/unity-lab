using UnityEngine;

// Wall turret that tracks the player through a full 360 degrees with a limited turn rate.
// The barrel visibly swings toward you, so the shot is readable and dodgeable;
// it fires along the barrel at your centre, which means going prone mid-swing can duck the shot.
public class ContraTurret : MonoBehaviour {
    public int hp = 3;
    public float interval = 1.7f;
    public float fireSpeed = 5.5f;
    public float turnSpeed = 200f;
    public float range = 15f;
    public float facing = -1f;
    public SpriteRenderer bodySr;

    float timer = 1.2f;
    float ang;
    Transform barrel;

    void Awake() {
        barrel = transform.Find("TurretBarrel");
        ang = facing < 0f ? 180f : 0f;
    }

    void Update() {
        Vector2 aimDir = new Vector2(facing, 0f);
        bool engaged = false;

        var ps = Object.FindObjectsByType<ContraPlayer>(FindObjectsSortMode.None);
        if (ps.Length > 0) {
            Vector2 d = (Vector2)(ps[0].transform.position - transform.position);
            if (d.magnitude <= range) { aimDir = d.normalized; engaged = true; }
        }

        float want = Mathf.Atan2(aimDir.y, aimDir.x) * Mathf.Rad2Deg;
        ang = Mathf.MoveTowardsAngle(ang, want, turnSpeed * Time.deltaTime);
        if (barrel != null) {
            float rad = ang * Mathf.Deg2Rad;
            barrel.localPosition = new Vector3(Mathf.Cos(rad), Mathf.Sin(rad), 0f) * 0.55f;
            barrel.localRotation = Quaternion.Euler(0f, 0f, ang);
        }

        timer -= Time.deltaTime;
        if (timer > 0f) return;
        timer = interval;

        if (!engaged) return;
        var cam = Camera.main;
        if (cam != null) {
            float halfW = cam.orthographicSize * cam.aspect;
            if (transform.position.x > cam.transform.position.x + halfW) return; // never fire from offscreen
        }
        if (Mathf.Abs(Mathf.DeltaAngle(ang, want)) > 20f) return; // still swinging: hold fire
        Fire(Quaternion.Euler(0f, 0f, ang) * Vector2.right);
    }

    void Fire(Vector2 dir) {
        var b = new GameObject("EnemyBullet");
        b.transform.position = transform.position + (Vector3)(dir * 0.85f);
        b.transform.SetParent(transform.parent, true);
        b.transform.localScale = new Vector3(0.38f, 0.18f, 1f);
        b.transform.rotation = Quaternion.Euler(0f, 0f, Mathf.Atan2(dir.y, dir.x) * Mathf.Rad2Deg);
        var sr = b.AddComponent<SpriteRenderer>();
        sr.sprite = GameSprites.Get();
        sr.color = new Color(1f, 0.45f, 0.1f);
        var bc = b.AddComponent<BoxCollider2D>();
        bc.isTrigger = true;
        var brb = b.AddComponent<Rigidbody2D>();
        brb.gravityScale = 0f;
        brb.linearVelocity = dir * fireSpeed;
        var bl = b.AddComponent<Bullet2D>();
        bl.enemyBullet = true;
    }

    public void Hit() {
        hp--;
        if (hp <= 0) {
            ContraState.score += 500;
            if (bodySr != null) bodySr.color = Color.white;
            Destroy(gameObject, 0.08f);
        } else if (bodySr != null) {
            bodySr.color = new Color(1f, 0.45f, 0.35f);
        }
    }
}
