---
name: volume-to-strut-lattice-stl-review
description: Transform STEP/STP volumes into strut-lattice structures with an optional inward cover and STL and Blender output. Supports local planar/curved surface layers, covered-mode powder ports, zero-thickness lattice-only mode, and parameter approval before transformation.
---

# Volume to strut-lattice structures with STL output

Create a separate strut-lattice output with an optional cover using FreeCAD and Blender. Preserve the
older lattice skills. Read [configuration](references/configuration.md) before
preparing a job and [performance choices](references/performance.md) when choosing
mesh detail or discussing speed. Keep the default 0.03 mm mesh deflection unless
the user chooses another export tolerance; lower fidelity is a design choice.

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

## Geometry and constraints

Use a valid single STEP solid and a true contained single-solid inward CAD offset,
default 2 mm. Preserve the source outer boundary. Reject failed offsets, split
cavities and invalid covers rather than approximating the CAD body.

Evaluate inner-cavity CAD normals locally. Support upward-facing planar and curved
roofs or ledges whose tangent inclination is strictly below 45Ã‚Â° to world XY.
Exclude downward floors, vertical walls and surfaces at the threshold. Build
direction is world +Z; reorient the source if another direction is wanted.

Default lower pitch is 12 mm, lower node/strut diameters 3.3/2.4 mm; top pitch is
6 mm with 5 mm nodes/struts. Preferred rise is 11.1 mm. Use two local node levels
beneath each roof region and minimum strut angle 50Ã‚Â° plus a 0.5Ã‚Â° selection margin.
Contacts must have finite CAD area and paths into retained boundary-connected
lattice or a cavity-floor fallback. Shorten/shift local drops when needed in
shallow regions; record actual drop ranges and fallback counts.

Inspect the actual side faces and choose a planar vertical side for the diamond
powder opening. The default dimensions are 12 Ãƒâ€” 18 mm, roof angle 56.31Ã‚Â° and
exclusion extending 6 mm beyond the inner wall. Ask if location is ambiguous;
never copy a fixture's face index/coordinates. The entire opening must fit.
Remove whole affected struts between nodes, including radius, and affected nodes;
omit unused nodes. Do not trim members at the port. Report excluded targets and
stop if a target outside the intended exclusion has no clear support route.

Surface coverage is sampled at top pitch plus adaptive CAD probes. This is not
a continuum proof or a guarantee for arbitrarily small features. Keep angle,
opening, contact and containment checks enabled when optimizing.

## Execution

Use fresh work/output paths and absolute script/configuration paths. Locate
FreeCADCmd and Blender, then run ordinary Python:

```text
python scripts/run_job.py CONFIG.json --freecad FREECADCMD_PATH --blender BLENDER_PATH
```

The runner saves stage logs and `timings.json`. It requires success markers as
FreeCAD can return zero after an exception. It does not resume incomplete jobs.
To run individual FreeCAD stages, set `SURFACE_LATTICE_CONFIG` to the absolute
configuration path and use job-local `-u` and `-s` settings if needed.

1. `prepare_cover.py`: inspect `source_faces.json` and `preparation.json`;
   require `SURFACE_COVER_PREPARED`.
2. `generate_members.py`: exact CAD clipping at boundaries, analytic conservative
   interior tests only after proving a planar convex cavity. Other geometry uses
   CAD clipping. Stream absolute-deflection member meshes to STL;
   require `SURFACE_MEMBERS_GENERATED`.
3. Blender `generate_covered_lattice.py -- CONFIG.json`: preserve overlapping
   facets using the supplied importer and save separate Cover/Lattice objects;
   require `SURFACE_LATTICE_ASSEMBLED`.
4. `validate_surface_lattice.py`: require `SURFACE_LATTICE_VALIDATION_OK` and
   `validation.json` status `PASS`. CAD geometry, port, contacts, angle and sampled
   coverage checks remain independent. Mesh edges and rounded facet composition
   use sorted disk batches. Proven convex-plane tests accelerate strict-interior
   mesh points; boundary points use CAD queries. Combined-mesh containment and
   port clearance follow from verified component facet composition.
5. Inspect a section through supported roof regions and the port. Deliver the
   full model with supported/excluded counts, removed struts, angle minimum,
   local-drop/fallback statistics, and report location. Sections are previews.

The scripts avoid a full Python triangle list during generation and hashing,
but exact CAD shapes, Blender assembly and sorting still require resources.
Do not promise a whole-job speedup from the neighbour-search benchmark.

Outputs include combined STL, Blender file, separate meshes, exact BREP geometry,
manifests, timings and validation. The mesh has intersecting closed members and
requires slicer union; it is not a verified fused solid. Validation does not
certify strength, complete powder evacuation, global connectivity or IN718
printability. It checks offset distance, not minimum wall thickness everywhere.

## Regression checks

Run `scripts/test_rules.py`. For geometry/export changes, use
`make_test_fixtures.py` with `SURFACE_LATTICE_TEST_DIR` pointing to an isolated
directory, then run both sloped/ledge and curved-roof fixture pipelines through
PASS. Check stream-writer orientation/composition and inspect a section after
changes affecting tessellation. Do not loosen checks to achieve a pass.

Test environment: Windows, FreeCAD 1.0.2, Blender 5.1.1. Benchmark results and
scope are documented in the performance reference; the large original body was
not regenerated to claim an end-to-end speedup.

Run `test_boundary_rules.py` with FreeCADCmd after uncovered-mode changes and require `UNCOVERED_BOUNDARY_TESTS_PASS`. Exercise covered and zero-thickness jobs, including sloped and curved roofs, through final export validation.
