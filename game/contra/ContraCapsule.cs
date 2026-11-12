using UnityEngine;

// Flying power-up: drifts left in a sine arc. Shoot it or touch it to get the spread gun.
public class ContraCapsule : MonoBehaviour {
    public float speed = 2.4f;
    public float centerY = -1.6f;
    public float amp = 0.35f;
    float t;

    void Update() {
        t += Time.deltaTime;
        var p = transform.position;
        p.x -= speed * Time.deltaTime;
        p.y = centerY + Mathf.Sin(t * 2.4f) * amp;
        transform.position = p;
        transform.rotation = Quaternion.Euler(0f, 0f, t * 90f); // spinning diamond reads as a pickup, not an enemy
        var cam = Camera.main;
        if (cam != null && p.x < cam.transform.position.x - 13f) Destroy(gameObject);
    }

    public void Collect() {
        var ps = Object.FindObjectsByType<ContraPlayer>(FindObjectsSortMode.None);
        if (ps.Length > 0) ps[0].spread = true;
        Destroy(gameObject);
    }
}
