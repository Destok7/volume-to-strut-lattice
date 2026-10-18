# Resource and fidelity choices

The previous scaled body had 37,935 closed CAD members, 30,449 struts and
7,621,744 combined triangles (381,087,284-byte binary STL). It already used
job-local convex-interior shortcuts and bounded-memory mesh validation. Those
features are included here, so they are not additional speedups over that run.

## Implemented without changing lattice parameters

| Change | Benefit | Cost or limit |
|---|---|---|
| Spatial buckets for lower-grid neighbour search | Avoid scanning an entire adjacent node layer | Extra indexing; CAD work still dominates |
| Stream tessellated members and concatenate binary STL payloads | Avoid retaining millions of Python triangles and duplicate FreeCAD mesh copies | More incremental I/O; exact CAD shapes remain in memory |
| Stream file hashing | Avoid reading large files into a single byte buffer | Hashing still reads every byte |
| Convex-interior analytic generation checks | Skip unnecessary Boolean clipping for proven contained primitives | Only planar convex cavities qualify; boundary/curved/concave cases keep CAD operations |
| Mesh audit in sorted disk batches | Bound Python memory; preserve edge balance and rounded facet-count comparison | Temporary disk space and sorting I/O; still checks all facets |
| Absolute CAD tessellation | Avoid unintended excess tessellation from relative shape settings | Export appearance depends on requested deflection and angular limit |
| Per-stage timings | Identify the real bottleneck for subsequent jobs | Small logging overhead; timing is environment dependent |

A benchmark at the large body's approximate bounds, with 0°, 17° and 90° lower
grid rotations, produced exactly identical nodes and ordered struts. Neighbour
search fell from approximately 2.0 seconds to 0.11–0.17 seconds (12–18× for that
step). This saves seconds, not the CAD-validation time. Full large-body runtime
and peak RAM have not been measured for this new version.

## Optional export tolerance

Keep `surface_support.mesh_deflection_mm` = 0.03 by default. Choosing 0.06 or
0.10 changes only the polygon approximation, not CAD member dimensions or CAD
validation tolerance. It increases the allowed CAD-to-mesh approximation and can
make small curves visibly faceted. The documented mesh containment allowance is
`2 * mesh_deflection_mm + validation.tolerance_mm` (0.07, 0.13 or 0.21 mm).
This allowance is a numerical check, not manufacturing accuracy.

Thirty members sampled at evenly spaced positions through the saved scaled CAD
compound yielded the following counts with absolute linear deflection and the
same 0.5 rad angular setting:

| Deflection | Sample triangles | Relative to 0.03 mm |
|---|---:|---:|
| 0.03 mm | 6,316 | 100% |
| 0.06 mm | 4,496 | 71.2% |
| 0.10 mm | 4,160 | 65.9% |

This small sample does not predict the whole part's exact size or runtime. Mesh
timings for this sample were too short/noisy to support a speed claim.

## Geometry changes requiring a deliberate choice

- Increasing lower pitch reduces cells and struts, often substantially. It also
  changes density, unsupported distances, stiffness and thermal behaviour.
- Increasing top pitch reduces roof contacts but increases unsupported roof spans.
- Reducing supports per node reduces material and member count but changes load
  paths and redundancy. Do not silently remove braces or targets to speed a run.
- Simplifying a STEP body can help CAD operations but changes the intended part.

## Other approaches, not implemented here

- A mesh-only preview pipeline could be much faster and omit Blender output if
  unnecessary. It would need a clearly different validation claim and robust mesh
  clipping for curved/concave shapes.
- Cached geometry/re-export can save repeat CAD work but needs source, parameter,
  kernel and artifact checks; do not reuse stale CAD based only on filenames.
- Parallel CAD processing can reduce wall time on suitable hardware but increases
  peak RAM and implementation complexity. It does not reduce total work.
- Skipping validation is not an optimization provided by this skill.
