# STEP job configuration

All dimensions are millimetres. Paths resolve relative to the configuration file.
Input and output must differ. Use fresh work/output paths. Inspect actual source
faces to choose the opening's face index and centre; values below are examples.

```json
{
  "input_step": "C:/parts/source.step",
  "work_dir": "C:/work/step_run1",
  "output_step": "C:/work/part_with_lattice.step",
  "cover": {"thickness_mm": 2.0},
  "powder_opening": {
    "face_index": 3,
    "center_mm": [40, 22, 12],
    "width_mm": 12.0,
    "height_mm": 18.0,
    "minimum_angle_deg": 50.0,
    "inward_clearance_mm": 6.0
  },
  "geometry": {
    "lower_pitch_mm": 12.0,
    "lower_node_diameter_mm": 3.3,
    "lower_strut_diameter_mm": 2.4,
    "top_pitch_mm": 6.0,
    "top_node_diameter_mm": 5.0,
    "top_strut_diameter_mm": 5.0,
    "layer_rise_mm": 11.1,
    "minimum_angle_deg": 50.0,
    "supports_per_node": 4,
    "top_layer_count": 2
  },
  "surface_support": {
    "angle_threshold_deg": 45.0,
    "sampling_deflection_mm": 0.1,
    "max_members": 20000
  },
  "build_frame": {"normal": [0,0,1], "x_hint": [1,0,0]},
  "validation": {"tolerance_mm": 0.01},
  "metadata": {"alloy": "IN718"}
}
```

| Parameter | Effect |
|---|---|
| cover.thickness_mm | CAD inward offset; outer boundary retained |
| opening face_index / center_mm | Position on an inspected planar vertical side |
| opening width / height | Diamond dimensions; roof inclination atan(height/width) |
| opening minimum_angle_deg | Minimum permitted diamond roof inclination |
| inward_clearance_mm | Extra excluded depth beyond the inner wall |
| lower_pitch_mm | Repeated lower lattice spacing in XY |
| lower node / strut diameters | Lower lattice feature dimensions |
| top_pitch_mm | Roof contact grid, supplemented by adaptive probes |
| top node / strut diameters | Local surface-support feature dimensions |
| layer_rise_mm | Lower layer spacing and preferred local support drop |
| geometry.minimum_angle_deg | Strut angle to XY, plus a 0.5Â° selection margin |
| supports_per_node | Maximum nearest connections/braces per stage |
| top_layer_count | Fixed at two local levels; other values rejected |
| angle_threshold_deg | Strict upper bound for local eligible roof inclination |
| sampling_deflection_mm | CAD tessellation used for adaptive roof probes, 0 < value â‰¤ 0.5 mm |
| max_members | Candidate/retained-member budget, not a geometry scale |
| build_frame.x_hint | Rotates the lower lattice in world XY |
| validation.tolerance_mm | CAD numerical tolerance, not printer accuracy |

There are no `output_stl`, `output_blend` or `mesh_deflection_mm` fields.
Do not copy a mesh configuration unchanged. Output extension must be `.step` or
`.stp`. Build normal is fixed to +Z. A failed STEP verification leaves an
unverified export for diagnosis; deliver only when final `validation.json` passes.

## Zero-thickness mode

Set `cover.thickness_mm` to `0` for lattice only. Omit `powder_opening`, or retain it as inactive settings. No cover or port clearance is emitted. Open strut ends are permitted only at local upper/lower boundaries; side-cut members and dangling interior ends are rejected. Local top sizing remains active; side-cut contact spheres are omitted and counted. See the cover-thickness modes in SKILL.md for validation scope.
