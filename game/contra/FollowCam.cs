using UnityEngine;

public class FollowCam : MonoBehaviour {
    public Transform target;
    public float minX = -50f;
    public float maxX = 50f;
    float advX; // classic Contra: camera never scrolls backward

    void Start() {
        advX = target != null ? target.position.x : minX;
    }

    void LateUpdate() {
        if (target != null && target.position.x > advX) advX = target.position.x;
        Vector3 p = transform.position;
        p.x = Mathf.Clamp(advX, minX, maxX);
        transform.position = p;
    }
}
