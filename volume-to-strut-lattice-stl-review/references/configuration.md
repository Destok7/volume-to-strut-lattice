# Configuration

All dimensions are millimetres. Paths resolve relative to the JSON file. Use
fresh work and output paths. The source must be one valid STEP/STP solid.

```json
{
  "input_step": "C:/parts/source.step",
  "work_dir": "C:/work/surface_run1",
  "output_stl": "C:/work/surface_run1/part.stl",
  "output_blend": "C:/work/surface_run1/part.blend",
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
    "mesh_deflection_mm": 0.03,
    "max_members": 20000
  },
  "build_frame": {"normal": [0,0,1], "x_hint": [1,0,0]},
  "validation": {"tolerance_mm": 0.01},
  "metadata": {"alloy": "IN718"}
}
```

Opening face/center are examples, not defaults: inspect the actual part.

| Parameter | Meaning |
|---|---|
| cover.thickness_mm | Positive: inward CAD offset; 0: uncovered lattice with no powder opening; negative: rejected |
| face_index / center_mm | Opening placement on a planar vertical outer face |
| opening width / height | Diamond dimensions; roof angle is atan(height/width) |
| opening minimum_angle_deg | Lower bound for diamond roof inclination |
| inward_clearance_mm | Extra exclusion depth beyond the inner wall |
| lower_pitch_mm | XY spacing of the staggered lower lattice |
| lower node / strut diameters | Lower lattice feature sizes |
| top_pitch_mm | Regular world-XY contact spacing, supplemented on small/trimmed regions |
| top node / strut diameters | Surface contact/lower local nodes and their connections |
| layer_rise_mm | Lower layer spacing and preferred local contact-to-lower-node drop |
| geometry.minimum_angle_deg | Member inclination to XY, with 0.5-degree selection margin |
| supports_per_node | Maximum nearest connections or braces per stage, subject to geometry |
| top_layer_count | Fixed at two local node levels; other values are rejected |
| surface_support.angle_threshold_deg | Strict upper bound on local roof/ledge angle to XY |
| sampling_deflection_mm | Curvature deflection used to seed adaptive CAD-normal probes |
| mesh_deflection_mm | CAD-to-STL tessellation deflection; replaces Blender bevel resolution |
| max_members | Budget guard for lattice candidates and retained members |
| build_frame.x_hint | Rotates the lower lattice in XY; surface contact grid remains world XY |
| validation.tolerance_mm | Numerical CAD tolerance, not printer accuracy |

For a cavity outward unit normal n, the roof angle is acos(n.z). Positive-Z
normals with angle <45 degrees qualify by default. Negative-Z floor normals
never qualify. Evaluate the CAD normal locally on curved surfaces, not one angle
per face. Exactly 45 degrees is excluded within a 1e-9-degree numerical guard.

Grid candidates are intersected with each CAD face. Additional contacts cover
adaptive probes within top_pitch/sqrt(2) in 3D on the same face. Probe triangles
are subdivided at approximately top_pitch/2; curvature tessellation also affects
sampling. This finite test cannot establish continuous or sub-resolution coverage.

The first local node lies on the inner cover so its clipped sphere has finite
contact area. The second normally lies one rise below it. Nodes may shift, or
the drop may halve/quarter, to obtain a clear route. In shallow cavities the
preferred drop is capped at half the local cavity depth. A floor connection is
used when no suitable connected lower-lattice node is available. Its strut uses
the top diameter and may be longer than one layer rise; report these fallbacks.

The requested surface-selection angle (45 degrees) and the minimum strut angle
(50 degrees plus selection margin) have different jobs. Changing one must not
silently change the other.

Coverage inside the intentional powder clearance is excluded and reported. An
unroutable target elsewhere stops generation. Curved supports do not expand the
port-placement rule to curved walls. Invalid or multi-solid CAD offsets stop the
job. STL input, old surface_contact/keepout/clipping options, arbitrary build
normals and the old bevel_resolution setting are not supported.

CAD clipping is slower than planar clipping. Outputs preserve intersecting closed
members instead of a CAD union. Exact CAD containment and sampled contact checks
do not prove mechanical strength, continuous surface support, full evacuation or
printability. The STL containment check allows 2 Ã— mesh_deflection + tolerance
for the curved tessellation; CAD containment uses the configured CAD tolerance.

## Zero-thickness mode

Set `cover.thickness_mm` to `0` for lattice only. Omit `powder_opening`, or retain it as inactive settings. No cover or port clearance is emitted. Open strut ends are permitted only at local upper/lower boundaries; side-cut members and dangling interior ends are rejected. Local top sizing remains active; side-cut contact spheres are omitted and counted. See the cover-thickness modes in SKILL.md for validation scope.
