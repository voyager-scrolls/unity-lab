# Reference deconstruction schema

One JSON per reference image, at `specs/reference/<name>.json`. It is the build order for a
reference-driven stage: every visible element is calibrated to metres, matched to a catalog
prefab, and grouped into a zone. The layout generator is written against this file, not against
freehand numbers.

```json
{
  "name": "bank_scene",
  "image": "C:/Users/ABCD/Downloads/Bank_robbery_map_scene_74c35317_2K.jpg",
  "size_px": [2048, 1152],
  "camera": {
    "horizon_row": 620,
    "cx_px": 1024,
    "hfov_deg": 60,
    "f_px": 1774.0,
    "h_m": 2.35,
    "ref_width_m": 5.0,
    "ref_px": [900, 900, 1210, 900]
  },
  "footprint_m": { "x": [-30, 30], "z": [-40, 0] },
  "palette": [
    { "hex": "#C9C2B4", "share": 0.31, "class": "warm stone" },
    { "hex": "#2B2B2E", "share": 0.12, "class": "tactical black" }
  ],
  "zones": [
    { "id": "Z1", "label": "facade apron", "bounds_m": [[-12, -8], [12, 0]], "elements": ["E01", "E02"] }
  ],
  "elements": [
    {
      "id": "E01",
      "label": "bank entrance portal",
      "screen_box": [840, 420, 1200, 760],
      "world_m": [0, 0],
      "size_m": [5.0, 1.0, 3.0],
      "size_min": [4.0, 0.4, 2.5],
      "size_max": [6.0, 2.0, 4.0],
      "category": "Environment",
      "prefab": "SM_Env_Wall_Exterior_01",
      "match": "approx",
      "match_note": "doorway built from wall modules + VaultDoor_Frame",
      "required": true,
      "qty": 1
    }
  ],
  "acceptance": {
    "shots": ["ref_cam", "ext_wide", "ext_elevated"],
    "min_ssim": 0.55
  }
}
```

## Field rules

- `camera`: produced by `tools/calib.py solve`. `f_px` and `h_m` are derived; `ref_px`/`ref_width_m` are the only hand inputs.
- `world_m`: `[X, Z]` on the ground plane, from `tools/calib.py point`.
- `size_m`: `[width, depth, height]` in metres, measured from the calibrated photo.
- `size_min` / `size_max`: acceptable envelope for `tools/match.py`; keeps a 2.6 m case out of a 1.2 m slot.
- `match`: `exact` (name + envelope), `approx` (composed from modules or near size), `none` (needs a custom Blender prop).
- `required`: false means it may be dropped for performance without re-approval.
- `acceptance.min_ssim`: the floor for `tools/compare.py diff` from the reference camera before a player build is proposed.
