---
name: volume-to-strut-lattice-stp-review
description: Transform STEP/STP volumes into strut-lattice structures with an optional inward cover and STEP/STP CAD output. Supports local planar/curved surface layers, covered-mode powder ports, zero-thickness lattice-only mode, and parameter approval before transformation.
---

# Volume to strut-lattice structures with STEP output

Create a separate STEP file containing retained strut-lattice members and an optional cover as
individual solids in a compound. Use FreeCADCmd; Blender is not required. Preserve
other lattice skills. Read [configuration](references/configuration.md) before
creating a job.

## Cover thickness modes

`cover.thickness_mm` defaults to 2 mm. Positive values use the covered workflow
below. Zero selects an uncovered strut lattice: use the exact source solid as the
clipping boundary, export no cover, and disable the powder opening and its entire
member-exclusion zone. Opening location is not required; show opening parameters
as inactive during review. Negative thickness is rejected.

For zero thickness, interior and side struts must connect to nodes at both ends.
Only the first and last local boundary layers may terminate openly at the lower
or upper source surface, including sloped and curved surfaces. Whole members
cut by vertical side surfaces are rejected. Local surface classification uses CAD
normals, with finite sampling on curved cut patches; it is not a continuum proof.
Interior leaf branches are pruned recursively, including branches capped by a node sphere. Unused nodes are omitted. This restriction can leave a gap along side walls.

Retain local top-node/strut sizing beneath eligible upper surfaces. Since there is
no physical roof to support, omit candidate contact spheres cut by a side and
report their count. Coverage validation in uncovered mode applies only to the
remaining side-safe surface probes, not to a continuous outer skin. Boundary
roots represent geometric termination at the original volume, not attachment to
a cover. No cover or powder-evacuation certification is implied.

## Parameter review before transformation

Before transforming a supplied body, show all editable parameters and ask:

> Would you like to edit any parameters, or proceed with these settings?

Wait for explicit approval of the displayed settings before starting the full
transformation. A request to use this skill, an attached file, or a request for
standard parameters alone does not approve settings that have not been shown.
If the user already reviewed and explicitly approved the same body, output and
settings in this chat, continue without repeating the question. Respect an
explicit user instruction to waive this review for that job.

Read the current defaults and supported fields from `scripts/common.py` and the
configuration reference. Apply values already specified by the user. Display
friendly names, configuration keys, proposed values, units and short effects.
Use compact grouped tables covering every editable item:

- Cover thickness; opening face and centre X/Y/Z, width, height, minimum roof
  angle and inward clearance.
- Lower pitch, lower node/strut diameters, top pitch, top node/strut diameters,
  layer rise, minimum strut angle and supports per node.
- Surface-angle threshold, sampling deflection, member budget, XY orientation
  (`build_frame.x_hint`) and CAD validation tolerance.
- Output format supported by this variant, input/output/work paths, and any
  supported descriptive fields (`metadata`, `object_name`). Label metadata as
  descriptive; it does not change material behaviour or geometry.
- For the STL variant, additionally show mesh deflection. The STEP variant has
  no mesh-deflection field; do not offer one or imply that STEP needs Blender.

Separately identify fixed settings: +Z build direction and two local node
levels. Explain that strut selection adds a fixed 0.5Ã‚Â° margin. Do not offer fixed
settings as editable. Explain whole-strut removal and separate/intersecting CAD
members or mesh shells as applicable; fusion is not a selectable implemented mode.

Cheap read-only source inspection for dimensions, validity and side-face choices
may happen before approval. Do not run the transformation pipeline, inward cover
construction, support generation, full validation, export or a costly benchmark
to obtain approval. Propose a powder-port location from actual inspected faces;
mark unresolved placement clearly. Do not silently adopt fixture coordinates or
resize an opening. Approval requires resolved active geometry settings; opening settings are inactive at zero thickness.

When reliable benchmarks exist, show a clearly labelled time range and its
basis/confidence. Otherwise say that a reliable time/resource estimate is not
available. Historical averages are not predictions; no automatic time estimator
is implemented. Do not launch a pilot without authorization.

If changes are requested, update the table and obtain approval for the revised
settings. Save the approved configuration in the job folder. Approval applies
to that source body, output and parameter set. Reopen review for material changes
to geometry parameters or port placement; routine implementation details and
reversible corrections within the approved configuration do not need new approval.

## Geometry

Use one valid STEP/STP solid. With positive thickness, create a true contained
single-solid inward CAD offset (default 2 mm) and one valid cover. Preserve the
original outer shape in covered mode; uncovered mode preserves the clipping
envelope rather than a continuous outer skin. Stop on
invalid offsets, split cavities or disappearing features instead of approximating
the CAD geometry.

Support upward-facing inner roofs/ledges whose local CAD tangent is strictly
below 45Ã‚Â° to world XY, including curved regions. Exclude floors and surfaces at
the threshold. World +Z is the build direction. Default lower pitch is 12 mm,
node/strut diameters 3.3/2.4 mm; top pitch is 6 mm with 5 mm nodes/struts.
Preferred rise is 11.1 mm and minimum strut angle is 50Ã‚Â° plus a 0.5Ã‚Â° selection
margin. Two local node levels follow each eligible roof region. Require finite
CAD contact area and paths to boundary-connected lattice or floor fallbacks.
Record shorter/shifted drops used in shallow cavities and fallback counts.

In positive-thickness mode, choose an inspected planar vertical side face for the powder opening. Default
diamond dimensions are 12 Ãƒâ€” 18 mm, roof angle 56.31Ã‚Â°, and exclusion extending
6 mm beyond the inner wall. Ask when location is ambiguous; never copy fixture
coordinates. The complete diamond must fit. Remove whole affected struts and
nodes, considering their radii, then omit unused nodes. Do not trim at the port.
Report targets excluded by the intentional opening; stop on unsupported targets
elsewhere. Surface coverage is sampled, not a continuum guarantee.

## Run

Use fresh work/output paths. Run ordinary Python with absolute paths:

```text
python scripts/run_job.py CONFIG.json --freecad FREECADCMD_PATH
```

The runner performs prepare, member generation, independent CAD validation and
STEP export/round-trip verification. It writes stage logs and `timings.json`.
FreeCAD can exit zero after an exception, so require each stage marker. For
manual stages set `SURFACE_LATTICE_CONFIG` to the absolute configuration path
and use job-local FreeCAD `-u` and `-s` settings when required.

- `prepare_cover.py`: `SURFACE_COVER_PREPARED`; inspect `source_faces.json` and
  `preparation.json`.
- `generate_members.py`: `SURFACE_MEMBERS_GENERATED`; exact clipped CAD members,
  conservative interior shortcuts for proven planar convex cavities, no output
  tessellation.
- `validate_surface_lattice.py`: `SURFACE_CAD_VALIDATION_OK` and
  `cad_validation.json` PASS. Verify source/config/artifact hashes, validity,
  containment, offset distance, member angles/attachments, port clearance,
  contact paths, finite contact areas and independently sampled roof coverage.
- `assemble_step_lattice.py`: `SURFACE_STEP_VALIDATION_OK` and `validation.json` PASS with
  `step_roundtrip` PASS. Export a compound, reopen it, match solids without
  assuming STEP order, verify validity and two-way Boolean volume differences.
  Complete positive spheres and cylinders may use equivalent defining-parameter
  checks at 1e-7 mm instead of Booleans. Recognize full spherical surfaces and
  full circular cylinder caps; do not apply this shortcut to trimmed members.
  BREP bounds and integrated mass properties can change numerically after STEP
  reload; record volume differences rather than using them as exact hashes.
  Require one-to-one member correspondence. When coincident-surface Booleans
  fail, use the documented finite CAD-surface distance audit in both directions,
  with boundary samples and tessellation-seeded face samples. Report every such
  fallback and its maximum sampled distance; do not claim a continuum proof.

Inspect a section through eligible roofs and the opening. Preview meshes may be
created separately for visualization but are not manufacturing outputs or part
of this STEP-only pipeline. Report counts, angle minimum, removed struts, drop
range, fallbacks, output size and timings. Do not claim an end-to-end improvement
from an export-only benchmark or a reuse of previously validated geometry.

## Output limits

The STEP contains intersecting individual solids and is not fused. It preserves
analytic CAD surfaces but may still be large or slow to open with many members.
The receiving CAD system's assembly/body interpretation must be checked there.
Do not fuse or simplify the geometry merely to reduce file size.

STEP has no mesh-deflection setting. `sampling_deflection_mm` still controls
adaptive roof probes; it does not approximate the exported CAD surfaces.
CAD computation and round-trip checks can remain expensive. Validation does not
certify strength, complete powder evacuation, global connectivity or IN718
printability. Offset distance is not a minimum-thickness proof everywhere.

Failed exports remain unverified. For an unchanged configuration and passing
`cad_validation.json`, a manual recheck may set `STEP_VERIFY_EXISTING=1` and rerun
`assemble_step_lattice.py`; this revalidates the existing export rather than
overwriting it. The runner always starts a fresh job. Never alter validation
hashes to reuse changed configuration or source data.

## Regression

Run `scripts/test_rules.py` with ordinary Python and `scripts/test_step_export.py`
with FreeCADCmd (require `STEP_EXPORT_TESTS_PASS`). After geometry/export changes, create isolated
sloped/ledge and curved fixtures using `make_test_fixtures.py` with
`SURFACE_LATTICE_TEST_DIR`, then run both pipelines to final PASS. Verify member
counts, contacts, angle selection and STEP round-trip differences. Test export
failure cases when changing matching logic. Do not loosen checks for a pass.

Tested environment: FreeCAD 1.0.2 on Windows. The STEP-only workflow does not
require Blender.



Run `test_boundary_rules.py` with FreeCADCmd after uncovered-mode changes and require `UNCOVERED_BOUNDARY_TESTS_PASS`. Exercise covered and zero-thickness jobs, including sloped and curved roofs, through final export validation.
