using UnityEngine;

public class Bullet2D : MonoBehaviour {
    public Collider2D ignore;
    public bool enemyBullet;

    void Start() {
        Destroy(gameObject, 2f);
    }

    void OnTriggerEnter2D(Collider2D other) {
        if (other == null || other == ignore) return;
        if (enemyBullet) {
            var p = other.GetComponentInParent<ContraPlayer>();
            if (p != null) p.Kill();
        } else {
            // GetComponentInParent: targets may be hit on a child collider (turret body, crate, body sprite)
            var cap = other.GetComponentInParent<ContraCapsule>();
            if (cap != null) { cap.Collect(); Destroy(gameObject); return; }
            var e = other.GetComponentInParent<ContraEnemy>();
            if (e != null) { e.Die(); Destroy(gameObject); return; }
            var j = other.GetComponentInParent<ContraJumper>();
            if (j != null) { j.Die(); Destroy(gameObject); return; }
            var t = other.GetComponentInParent<ContraTurret>();
            if (t != null) { t.Hit(); Destroy(gameObject); return; }
        }
        Destroy(gameObject);
    }
}
