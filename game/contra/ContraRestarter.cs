using UnityEngine;

// Survives the ContraGame root destroy; rebuilds the level once after player death.
// Root renamed BEFORE destroy so Build()'s find-guard passes in the same frame.
public class ContraRestarter : MonoBehaviour {
    float t;
    float delay;

    public static void Schedule(float d) {
        var go = new GameObject("ContraRestarter");
        var r = go.AddComponent<ContraRestarter>();
        r.delay = d;
    }

    void Update() {
        t += Time.deltaTime;
        if (t < delay) return;
        var old = GameObject.Find("ContraGame");
        if (old != null) {
            old.name = "ContraGameOld";
            Object.Destroy(old);
        }
        ContraBoot.Build();
        Destroy(gameObject);
    }
}
