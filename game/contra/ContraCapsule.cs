using UnityEngine;

// Flying power-up: drifts left in a sine arc. Shoot it or touch it to get the spread gun.
public class ContraCapsule : MonoBehaviour {
    public float speed = 2.6f;
    public float centerY = -1.1f;
    public float amp = 0.9f;
    float t;

    void Update() {
        t += Time.deltaTime;
        var p = transform.position;
        p.x -= speed * Time.deltaTime;
        p.y = centerY + Mathf.Sin(t * 2.4f) * amp;
        transform.position = p;
        var cam = Camera.main;
        if (cam != null && p.x < cam.transform.position.x - 13f) Destroy(gameObject);
    }

    public void Collect() {
        var ps = Object.FindObjectsByType<ContraPlayer>(FindObjectsSortMode.None);
        if (ps.Length > 0) ps[0].spread = true;
        Destroy(gameObject);
    }
}
