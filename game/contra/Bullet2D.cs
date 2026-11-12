using UnityEngine;

public class Bullet2D : MonoBehaviour {
    public Collider2D ignore;
    public bool enemyBullet;

    void Start() {
        Destroy(gameObject, 2f);
    }

    void OnTriggerEnter2D(Collider2D other) {
        if (other == ignore) return;
        if (enemyBullet) {
            var p = other.GetComponent<ContraPlayer>();
            if (p != null) p.Kill();
        } else {
            var e = other.GetComponent<ContraEnemy>();
            if (e != null) e.Die();
            var j = other.GetComponent<ContraJumper>();
            if (j != null) j.Die();
            var t = other.GetComponent<ContraTurret>();
            if (t != null) t.Hit();
            var c = other.GetComponent<ContraCapsule>();
            if (c != null) c.Collect();
        }
        Destroy(gameObject);
    }
}
