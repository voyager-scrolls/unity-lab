using UnityEngine;

public class Bullet2D : MonoBehaviour {
    public Collider2D ignore;
    void Start() {
        Destroy(gameObject, 2f);
    }
    void OnTriggerEnter2D(Collider2D other) {
        if (other == ignore) return;
        var e = other.GetComponent<ContraEnemy>();
        if (e != null) e.Die();
        Destroy(gameObject);
    }
}
