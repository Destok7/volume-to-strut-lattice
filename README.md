# Volume to Strut-Lattice Structures for Codex

Two Codex skills for creating lattice infill inside a STEP/STP body, with an optional inward cover, local surface layers and (when covered) a diamond-shaped powder-removal opening. Both skills present the proposed parameters and wait for approval before starting the full transformation.

The workflows were developed for investigating volume support structures for additive manufacturing, including IN718 applications. Replacing a solid interior with lattice can reduce material use. Any reduction in production time depends on the printing process and must be evaluated separately.

## Available skills

| Skill | Main output | Required CAD software | Intended use |
|---|---|---|---|
| [`volume-to-strut-lattice-stp-review`](volume-to-strut-lattice-stp-review/SKILL.md) | STEP/STP containing separate CAD solids | FreeCAD | CAD exchange and inspection of analytic geometry |
| [`volume-to-strut-lattice-stl-review`](volume-to-strut-lattice-stl-review/SKILL.md) | STL and Blender `.blend` file | FreeCAD and Blender | Mesh inspection and downstream workflows that accept STL |

The skills share the same basic cover, lattice and support rules. Their export and export-validation stages differ. Each skill folder is self-contained; installing one does not require installing the other or any older lattice skill.

**Output members intersect but are not fused into one solid.** A STEP importer may expose many solids. Mesh-based downstream tools may need to unite overlapping volumes. Global Boolean fusion is not an implemented output option.

## What happens to the supplied body?

1. **The proposed settings are reviewed.** Codex can inspect the source dimensions and side faces, then shows the editable parameters. It asks whether changes are wanted and waits for approval.
2. **The boundary mode is selected.** Zero thickness uses the source volume directly with no cover or powder opening. With positive thickness, an inward cover is created. The source's outer boundary is retained, except where the approved powder port is cut. The default inward offset is 2 mm.
3. **A lower lattice fills the cavity.** Repeated cells use fixed feature dimensions; a larger part receives more cells rather than proportionally enlarged struts.
4. **Local supports follow eligible roofs and ledges.** Thicker nodes and struts connect to the inner cover beneath selected surface regions, including curved regions.
5. **The powder opening is cleared in covered mode.** At zero thickness this step and the whole port exclusion zone are disabled. Affected struts are removed completely between their nodes, rather than shortened at the opening. Affected and unused nodes are also omitted.
6. **The result is checked and exported.** Geometry checks remain enabled. The STEP workflow additionally reopens and compares its export; the STL workflow checks the generated mesh and assembles the Blender file.

The source file is retained. Generated files use separate output paths.

## Supported input and geometry limits

- Input is a **valid, single-solid STEP or STP body**. These two skills do not accept STL input.
- With positive cover thickness, the CAD kernel must produce one valid, contained inward cavity and one valid cover. Thin features, difficult curvature or inward corners can cause the offset to fail or split the cavity; not every otherwise valid STEP body is suitable.
- Build direction is fixed to **world +Z**. Reorient the source before processing if another build direction is required.
- In covered mode the powder port requires a **planar vertical side face**, and its entire outline must fit on that face. Its location is selected for the actual part; there is no universal face number or centre coordinate.
- Curved roofs are supported, but this does not permit placing the port on an arbitrary curved wall.
- The skill stops when a required target outside the intended powder clearance cannot be supported with a valid route.

## How roof support is selected

The skill evaluates the **inner cavity surface**. A region qualifies when its outward normal points upward and its local tangent inclination is **strictly below 45° to the XY plane**, by default. A horizontal roof qualifies. A surface at exactly 45°, a vertical side and a downward-facing floor do not.

For curved faces, the normal is evaluated locally; the complete face is not classified from one average angle. Contacts are placed on a regular XY grid and supplemented using adaptive CAD surface probes.

Two local node levels follow each eligible region at its own height. The preferred local drop is 11.1 mm. In shallow regions, nodes can move closer to the roof or shift to find a valid route. A connection to the cavity floor may be used when no suitable lower-lattice anchor is available. The report should identify reduced drops and floor fallbacks.

The **roof-selection angle** and the **strut angle** serve different purposes. The default roof threshold is 45°. The default minimum strut angle is 50°, with a fixed additional 0.5° selection margin.

Coverage is checked at sampled locations. It is not a guarantee of continuous support at every surface point or detection of arbitrarily small features.

## Uncovered mode: cover thickness = 0 mm

The original STEP solid is the clipping volume; it is not exported as a solid
skin. There is no cover, powder opening or port-induced member removal. Opening
face, centre, dimensions and clearance are inactive, and need not be supplied.
Negative thickness is rejected. The default remains 2 mm.

Interior and side struts must connect to nodes at both ends. Open structural
terminations are allowed only where the first/last local layers reach lower or
upper surfaces, including slopes and curves. These are not hollow tubes: each
exported strut remains a closed CAD solid or closed mesh shell. Whole members cut
by vertical side faces are omitted. Branches ending at interior leaf nodes are
pruned recursively, including ends capped by a node sphere; unused nodes are
omitted too. This may leave
a setback along the sides instead of reproducing a continuous outer surface.

The top node and strut sizes remain active beneath selected upper surfaces.
Contacts whose spheres would be cut by side walls are omitted and reported.
Surface coverage checks apply only to remaining side-safe probes. Boundary
classification uses exact planar face normals and finite CAD-normal sampling on
curved cut patches; it does not establish continuous coverage or connectivity of
every lattice component. Open-ended interior members and side cuts are checked
again in validation.

Use `"cover": {"thickness_mm": 0}` in either configuration. The parameter review
must show this mode and mark opening controls inactive before approval.

## Editable parameters

All dimensions below are in **millimetres**, unless stated otherwise. Values describe the supplied defaults, not settings suitable for every part. Full configuration keys and examples are in each skill's `references/configuration.md`.

### Cover and powder opening

| Parameter | Default | Responsibility |
|---|---:|---|
| Cover thickness | 2.0 | Positive: inward cover; 0: uncovered lattice; negative: invalid |
| Opening face and centre X/Y/Z | Selected for the part | Position of the diamond on an inspected side face |
| Opening width | 12.0 | Horizontal diamond dimension |
| Opening height | 18.0 | Vertical diamond dimension |
| Minimum opening roof angle | 50° | Rejects opening proportions with an insufficient roof inclination |
| Inward clearance | 6.0 | Additional lattice exclusion beyond the inner cover wall |

For a 12 × 18 mm diamond, the roof inclination is `atan(18/12)`, approximately 56.31°. This geometric angle does not, by itself, certify support-free printing or effective powder evacuation. The conservative member-clearance test can remove extra members near opening corners.

### Lattice geometry

| Parameter | Default | Responsibility |
|---|---:|---|
| Lower cell pitch | 12.0 | XY spacing of the repeated lower lattice |
| Lower node diameter | 3.3 | Size of lower lattice nodes |
| Lower strut diameter | 2.4 | Thickness of lower lattice struts |
| Top contact pitch | 6.0 | Regular XY spacing of roof contacts, with additional sampled-region contacts where needed |
| Top node diameter | 5.0 | Size of local roof-support nodes |
| Top strut diameter | 5.0 | Thickness of local roof-support struts |
| Layer rise | 11.1 | Lower-layer spacing and preferred local support drop |
| Minimum strut angle | 50° | Minimum inclination to XY, before the fixed 0.5° selection margin |
| Supports per node | 4 | Maximum nearest connections or braces per stage, subject to geometric constraints |
| XY orientation hint | `[1, 0, 0]` | Rotates the lower lattice within XY; the roof-contact grid stays aligned to world XY |

Lower pitch generally creates more members and smaller cells. Larger diameters generally add material and reduce free space. These changes also affect load paths, heat flow and powder access; the scripts do not calculate those process effects.

### Sampling, computation and output

| Parameter | Default | Responsibility |
|---|---:|---|
| Surface-angle threshold | 45° | Strict upper limit for eligible local roof/ledge inclination |
| Sampling deflection | 0.1 | CAD tessellation setting used to seed adaptive surface probes |
| Member budget | 20,000 | Guard against excessive candidate/retained-member counts; larger jobs may need an explicitly reviewed increase |
| CAD validation tolerance | 0.01 | Numerical geometry-check tolerance; not printer accuracy |
| STL mesh deflection | 0.03 | Polygon approximation for STL output; **STL skill only** |
| Input, work and output paths | Job-specific | Source location, temporary work folder and destination files |
| Descriptive metadata | Job-specific | Labels such as alloy information; does not apply a material or manufacturing model |

STL mesh deflection must be greater than zero and no more than 0.10 mm. Increasing it can reduce triangle count and file size while producing a coarser approximation of curves. It does not change CAD pitch or strut dimensions. STEP output has no mesh-deflection parameter; its sampling deflection still matters for roof probing.

**Fixed settings:** +Z build direction and two local support-node levels. The fixed 0.5° strut-selection margin is not a separate editable field. Not all combinations of editable values are valid; configuration and geometry checks reject unsupported combinations.

## Requirements

| Component | STEP skill | STL skill |
|---|---|---|
| Codex with local file access and script execution | Required | Required |
| FreeCAD, including `FreeCADCmd` | Required | Required |
| Blender executable | Not required | Required |
| Python 3 for the command-line runner | Required when using the runner | Required when using the runner |
| FreeCAD MCP or another live-control add-on | Not required | Not required |

The geometry engine uses FreeCAD's bundled Python modules. An ordinary Python installation alone does not replace FreeCAD. Executable and file paths must match the user's computer.

The tested environment was **Windows, FreeCAD 1.0.2 and Blender 5.1.1**. These are the tested versions, not a verified minimum-version specification. Other versions and operating systems require compatibility checks before their use is claimed as supported.

Publishing a skill on GitHub does not install its CAD dependencies or cause transformations to run on GitHub servers.

## Installation in Codex

Keep each complete skill folder intact, including `SKILL.md`, `scripts/`, `references/` and `agents/`. Publishing only `SKILL.md` is insufficient for these script-backed skills.

After publishing this repository, give Codex the URL of the desired **skill folder** and ask, for example:

> Use `$skill-installer` to install the skill from `https://github.com/YOUR-USERNAME/YOUR-REPOSITORY/tree/main/volume-to-strut-lattice-stp-review`.

Replace the username, repository and branch placeholders. For the mesh workflow, use the folder `volume-to-strut-lattice-stl-review` instead. A private repository requires suitable access.

For background on skill packaging, see the [official OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills).

## Example request

Attach a STEP/STP body in a new Codex chat and write:

> Use `volume-to-strut-lattice-stp-review` for the attached body. Start with standard parameters and propose a powder-removal opening near the bottom. Show all editable parameters and wait for my approval before transforming it.

For STL and Blender output, substitute `volume-to-strut-lattice-stl-review`.

Codex first reviews the proposed values and unresolved placement choices. If changes are requested, it updates the settings for review. An explicit approval applies to that body, output and parameter set. Material changes reopen the review. The Python runners themselves do not display an interactive approval dialog: this checkpoint is part of the Codex skill instructions.

## Output and validation

The **STEP skill** creates a STEP/STP compound containing the retained lattice solids and, when enabled, the cover. It also retains BREP geometry, configuration/manifests, logs, stage timings and validation reports. It performs independent CAD checks and reopens the STEP to verify one-to-one member correspondence. Complete spheres and cylinders can use defining-parameter checks; other members use two-way Boolean geometry comparisons. Documented finite surface-distance audits are available for coincident-surface comparison failures and are recorded in the report.

The **STL skill** creates a combined STL and a Blender file with a lattice object and an optional cover object, together with working CAD files, component meshes, manifests, timings and validation reports. Export verification checks mesh containment with a documented tessellation allowance, powder-port clearance, balanced mesh edges and component-facet composition. It does not establish a single fused manifold solid.

Both workflows check source/configuration consistency, CAD containment, member geometry and angles, attachments, finite roof contacts, sampled coverage and opening clearance. A finished result requires the applicable final validation report to state **PASS**. Failed or partial exports may remain for diagnosis and should not be treated as approved results.

## Performance and large files

Runtime depends on geometry, member count, boundary clipping, surface sampling, tessellation, validation and hardware. A smaller file is not necessarily quicker to display.

The implementation uses spatial neighbour searches and conservative interior shortcuts. The STL version also streams mesh output and uses disk batches for mesh verification. STEP avoids STL tessellation, mesh audits and Blender assembly, but adds STEP writing, reading and round-trip checks. Neither output approach is always faster.

In one completed large example, approximately 38,000 solids produced a 112 MB STEP and a 381 MB STL. Although STEP was smaller, its GUI import and interaction were difficult on the user's machine. This is an example, not a general performance guarantee. CAD software may struggle to display tens of thousands of separate solids, while a mesh viewer handles the STL more smoothly.

There is **no automatic transformation-time predictor**. `timings.json` records actual stage times during execution. Before approval, a time/resource estimate should be provided only when comparable benchmarks support it, with its basis and confidence stated. Otherwise the estimate should be identified as unavailable or low confidence. A costly pilot requires separate authorization.

## Engineering limitations

These are geometry-generation and checking tools. Their results do not certify mechanical strength, thermal behaviour, print parameters, fatigue life, complete powder evacuation or support-free IN718 manufacturing. Alloy metadata does not perform material simulation.

The inward-offset check does not prove minimum wall thickness everywhere on arbitrary curved surfaces. Sampled coverage is not a continuum proof. The checks do not certify global connectivity of every retained lattice member. STEP and STL outputs contain intersecting members; downstream handling must be assessed for the intended CAD, slicing or manufacturing software.

## Repository contents and sharing

```text
README.md
volume-to-strut-lattice-stp-review/
  SKILL.md
  agents/
  references/
  scripts/
volume-to-strut-lattice-stl-review/
  SKILL.md
  agents/
  references/
  scripts/
```

Each skill includes its configuration reference and test helpers. Do not add generated customer models, job logs, personal configuration files or Python cache folders to the published package. Add the repository owner's chosen license before distributing it for reuse under those terms.
