using UnityEngine;

public class FollowCam : MonoBehaviour {
    public Transform target;
    public float minX = -26f;
    public float maxX = 26f;
    void LateUpdate() {
        if (target == null) return;
        Vector3 p = transform.position;
        p.x = Mathf.Clamp(target.position.x, minX, maxX);
        transform.position = p;
    }
}
