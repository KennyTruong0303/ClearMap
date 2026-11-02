# ClearMap improvement log

## Purpose and working agreement

Build a locally tested ClearMap improvement branch from controlled demo
experiments, then validate on representative data before remote use. The eventual
goal is an agent integrated into ClearMap: it runs analysis, presents evidence,
records decisions, and pauses at human scientific review checkpoints. No agent
integration or production detector changes have been implemented yet.

Architecture clarification, 2026-10-26: the user wants both pipeline execution
and the separate QC review to use subscription-backed agent sessions. No OpenAI
API key or separately billed OpenAI API dependency is planned. Replace the
previous Astra-specific QC role with a separate subscription-agent QC reviewer.
The execution agent prepares reproducible outputs and evidence; the QC session
reviews that evidence separately and records findings, uncertainty and recommended
acceptance/rework; the human retains the agreed scientific approval checkpoints.
Separate sessions do not guarantee independent errors or biological correctness.
The eventual ClearMap integration should exchange run manifests, images, metrics
and review decisions through local artifacts. The exact supported session launch,
authentication and handoff mechanism must be verified before implementation;
this plan does not assume an API key, unrestricted unattended subscription access,
or an already implemented in-process agent. Subscription limits or required
interaction should leave the run resumable and awaiting review, not auto-approved.

Keep original ClearMap separate. Experiments and evidence live in iDisco-analysis;
reviewed code changes will belong in ClearMap-work. Preserve provenance, input
hashes, parameters, before/after outputs, uncertainty and human decisions.

## Human labels — 2026-10-26

NEATmap image 25, frame index 5, channel 0; coordinates below are crop pixels.
- C, right crop (190,170): user says one object. This is a visual object label,
  not independent proof of biological cell identity.
- A, center (15,190), and B, center (136,142): user is uncertain whether cell or
  background. Neither is a positive nor a negative training/tuning label.
- Earlier upper object, right near (150,39): user judged one cell; provisional.
- Earlier center objects near (113,43), (33,138), (98,113): provisional single
  objects from the previous review. Approximate anchors, not exact masks.

User priority: improve clear cases first, revisit borderline cases afterwards.

## Confirmed defects and evidence

1. Tied peak plateaus yield multiple seeds with h_max=None.
   Evidence: peak-plateau-review.md and its linked synthetic/demo outputs.
2. Original overlapping weighted markers add categorical seed IDs, producing
   false IDs, remote label collisions and loss of seed pixels. Single-threading
   does not repair this. Evidence: direct-marker-review.md, including A/B/C.
3. Parallel weighted marker writes race. Evidence: thread-trace-review.md.

## Combined experiment — 2026-10-26

Script: compare_combined_markers.py.
Output: test-data/combined-markers-20261026T033506928406Z/.

Compared direct markers alone against direct markers plus face-connected,
equal-valued plateau collapse. Fixed threshold 168, maxima 11x11x1, background
21x21 and accepted size 5–500. No distance merge or threshold adjustment.
Direct shapes exactly matched the previous saved experiment. Three watershed
repeats per crop/variant were identical. This is a stage-level comparison, not
a newly run end-to-end pipeline or a general accuracy evaluation.

| Reviewed target | Direct only | Combined | Interpretation |
|---|---|---|---|
| C | Two seeds; regions 5 and 3 pixels | One seed; region 8 pixels | Removes the artificial split; matches the one-object label |
| Center object 1 | One accepted region, 81 pixels | Same | Preserved |
| Center object 2 | One accepted region, 33 pixels | Same | Preserved; separate one-pixel excluded seed in review window |
| Center object 3 | One accepted region, 11 pixels | Same | Preserved; separate one-pixel excluded seed in review window |
| Upper right object | Two accepted regions, 24 and 17 pixels | Same | Unresolved disconnected-peak duplicate |

Crop-wide accepted totals: center 25 to 24, right 21 to 18. These totals do not
measure accuracy; other changed objects were not human-validated in this test.
The eight-pixel C region is its above-threshold footprint, not a validated full
cell boundary. Figure inspected visually. Different colors across methods
reflect renumbered labels, not necessarily changed boundaries.

## Integration plan and next checkpoint

### Manual reference pilot prepared — 2026-10-26

User authorized preparing a small manually reviewed 3D reference set.
build_reference_review.py and reference_review_template.html create a self-contained
local review page at test-data/reference-review-v1/review.html, with source hashes,
six fixed disjoint windows, voxel spacing and a prospective tuning/held-out split
in manifest.json. Automatic detections are hidden. Labels are provisional objects,
uncertain, artifact or edge; completion is recorded separately per region.
No human labels or biological accuracy scores exist yet. See
REFERENCE_REVIEW_PROTOCOL.md for rules, limitations and later evaluation criteria.

Browser smoke check: actual grayscale plane rendered; a test mark appeared with
XYZ coordinates; Next Z changed the displayed plane; Undo removed the test mark.
Page returned to its initial plane with no labels. Export/import code is present
but download/import round-trip has not yet been exercised in the UI. User must
download JSON to persist labels; no automatic saving is claimed.

### Public spatial sample and real preprocessing validation — 2026-10-26

Selected the official BrainGlobe cellfinder napari tutorial sample:
https://brainglobe.info/tutorials/cellfinder-detection.html.
Its tutorial explicitly specifies Z/Y/X spacing 5/2/2 micrometres and describes
a two-channel 3D sample with artifacts and imperfect detection. The pinned loader
at brainglobe/cellfinder commit 105f5942d1b9cac98d7a2d5ee591f9826eea5ab0,
cellfinder/napari/sample_data.py, stacks 30 planes on axis 0 and assigns ch0 Signal,
ch1 Background. Thus axes are ZYX; ClearMap inputs are transposed to XYZ.
Exact clearing protocol/stain/modality for this crop was not independently
established. Do not call it iDISCO or c-Fos validation.

fetch_public_3d.py downloaded 60 TIFFs (40,839,600 bytes total), verified file
sizes and Git blob hashes against the pinned tree, and recorded SHA256 values.
Each channel is uint16, shape (30,510,667). Manifest and inputs:
test-data/public-cellfinder-3d/manifest.json. No weights/models installed.

validate_public_3d.py evaluated three predefined 96×96×30 signal crops starting
at XY (128,128), (288,256), (480,352). Evidence:
test-data/public-3d-validation-20261026T123546237544Z/report.json,
orthogonal-qc.png and CSVs. Threshold stayed 168, background disk 21×21,
maxima 11×11×1 and plateau collapse unchanged. The Z-neighborhood of one was
retained deliberately, not calibrated to this sample. Actual ClearMap background
removal and maxima detection were rerun in every expanded context; seeds were
not synthetic/fixed. Components intersecting the ownership core, including those
without a currently owned seed, trigger expansion if cut by an artificial edge.

All three recovered coordinate sets and voxel masks exactly matched their
single-volume reference: 1,900 / 2,357 / 1,809 seeds. These are candidate counts,
NOT cell counts or accuracy estimates. New seed observations appeared during
context expansion (3,153 / 2,615 / 1,052 summed over overlapping contexts, not
unique new biological objects). No duplicate ownership was permitted.
Block expansions were 3/2/2, 1/2/1 and 0/2/1 respectively; context often reached
most or all of the available 30-plane stack. This limits any scaling claim.

On the first crop, actual full detect_cells single-block output matched every
reference coordinate and size. Using existing block ownership with machine
settings 10/16/overlap5 returned the same 1,900 coordinates but 421 mismatched
sizes. Both full runs used the experimental direct markers and component
segmentation; this is not a comparison against completely untouched ClearMap.
Context recovery matched all reference voxel masks. Its orchestration was still
the experimental stage runner, not a production detect_cells integration.

Visual orthogonal QC inspected. Frozen settings generate many candidates,
including noise; detected regions touching subvolume/acquisition faces numbered
785 / 394 / 225 and require QC. No biological labels or accuracy validation.
The real stack strengthens the block-consistency evidence; full-volume memory,
long-Z filter support, physical calibration, representative iDISCO data, and
orientation-invariant multi-seed boundaries remain unvalidated. Automatic merging
and production adoption remain disabled. Inputs/evidence are local and ignored
by Git; scripts and this record are versionable.

### Real 3D validation input audit — 2026-10-26

User requested validation with real 3D data and actual preprocessing/peak detection.
audit_3d_inputs.py recorded hashes and metadata in
test-data/3d-input-audit-20261026T122758403165Z/report.json.
Both NEATmap files are explicitly tagged TCYX, shape (10,2,788,2048), ImageJ
frames=10/channels=2, with no verified spatial Z or Z spacing. The accompanying
Note.txt names slice IDs and c-Fos/autofluorescence channels but does not establish
that frames are depth. Do not reinterpret them as Z. Previous 2D results remain
2D evidence. The other located spatial demo is a coarse registration volume;
it is not suitable for individual-cell validation.

Requested a local cell-resolution 3D stack path and XYZ voxel spacing, or the
user's preference to select a public sample. Real 3D validation has NOT run or
passed. Once suitable input is identified, freeze preprocessing/peak settings,
compare single-volume and block/context-recovery runs using actual detected
seeds (including newly discovered halo seeds), record physical-edge/incomplete
cases, and present QC before any production or threshold changes.

### Fixed ownership and context recovery — 2026-10-26

Experiment: test_block_ownership.py. Evidence:
test-data/block-ownership-20261026T114757741428Z/report.json.

Keep the original ClearMap valid core as the exclusive owner of each seed,
include ALL seeds in the segmentation context, and emit only owned results.
Before trusting a result, check whether its entire threshold-connected component
touches an artificial context edge. Expand along touched faces in bounded steps
(max(overlap,8) voxels in this diagnostic), preserving the original ownership.
Exhausted expansion returns needs_context with size=None, not a truncated size.
Components reaching the acquisition edge receive physical_edge_qc. Production
overlap and threshold settings remain unchanged.

All ten prior synthetic boundary cases matched single-volume voxel membership
per global seed identity, not merely total size. Ownership checks found no
missing or duplicate seeds. Compact cases required no expansion. With overlap 5,
the extended cell recovered 233 pixels and the competing pair recovered 131/110
after one expansion per owner. With overlap 32, the extended cell recovered 903
pixels after one expansion; the pair matched 131/110 without expansion.

Two failure-handling controls passed: zero expansion budget reports needs_context
with no size; a connected column reaching acquisition edges matches the reference
mask but remains flagged physical_edge_qc.

Scope: synthetic shape-stage proof with known seeds and actual ClearMap block/core
geometry. Arrays and reference markers are loaded globally for diagnostics; this
does not establish bounded-memory performance or full-detector integration. Real
peak finding, preprocessing support, seed discovery during expansion, and real 3D
data remain unvalidated. Large connected components can force large expansions.
Orientation-dependent ties inside components remain a separate unresolved issue.

Next: test ownership/context recovery with real 3D blocks and actual preprocessing
and peak detection, including faint bridges and newly discovered halo seeds.
Automatic merging remains disabled; no production implementation was changed.

### Claude Review 2 follow-up — 2026-10-26 (completed in requested order)

Reviewed REVIEW_FROM_CLAUDE_2026-10-26.md, prioritizing Review 2. The stray model
copy was already removed and was not restored. No production source, installed
package, configuration or threshold was changed. Automatic merging stayed off.

1. **Timing wording corrected.** Earlier measurements were for an entire
   256×256 crop, not one component. The old report gives 0.28–10.63 ms for the
   component method versus 0.45–1.22 ms globally across all crops. The sparse
   seeded crop is about 1.85x slower; therefore the review's 6.7–14.5x range
   does not describe every seeded crop. The log retains rounded 2–14x wording.

2. **Single-seed shortcut added to experimental segment().** The previous
   implementation is preserved as segment_reference(). A component containing
   one positive marker ID is assigned entirely to that ID; unseeded components
   remain zero. Multi-seed components still call watershed. Exact array equality
   against the reference is asserted on the existing 27 synthetic cases and all
   eight demo crops. Validation passed:
   test-data/component-validation-20261026T113739352945Z/report.json.
   The trace script now delegates to the same segment() implementation.
   Same-process three-repeat median benchmarks in
   test-data/review2-geodesic-20261026T113854689110Z/report.json show roughly
   3.25–8.42x speedup on seeded crops (0.45–2.98 ms per crop for the shortcut).
   This does not remove the remaining Python component loop or validate scaling.

3. **Geodesic tie-break tried; NOT accepted.** review2_geodesic.py starts with
   per-component watershed and reassigns whole connected equal-intensity plateaus
   that compete between labels using shortest face-connected distance to seeds
   inside the mask. Exact equal-distance ties are explicitly ambiguous (zero
   plus a separate ambiguity mask), not arbitrarily assigned by ID. This is a
   diagnostic; zero must not be interpreted as biological background or silently
   used for cell-size acceptance. Unit voxel steps are not physical distances.
   Under swap of axes 0/1 and each individual axis flip, flat 2D/3D synthetic
   cases become invariant, including ambiguity masks. But six of eight real
   crops still fail at least one transformation (14 failed transformed comparisons
   in total). Plateau selection inherits orientation-dependent watershed labels;
   this post-processing does not provide a general invariant segmentation.
   Evidence: the same review2-geodesic report. No corrected biological boundary
   claim is supported. The tested 3D swap is axes 0/1, not all permutations.

4. **Actual ClearMap block-boundary tests found remaining failures.**
   review2_blocks.py tests both repository machine config (size_min=10,
   size_max=16, overlap=5) and the detection API defaults (50,100,32), along Z,
   using actual split_into_blocks and detect_cells. Worker/native threads are
   limited to one; this tests blocking semantics rather than concurrent execution.
   Known peak masks isolate shape/block behavior; background preprocessing is
   disabled and threshold stays 168. It does not validate upstream peak finding.
   Final report: test-data/review2-blocks-20261026T114217189786Z/report.json.
   Global internal boundary is z=120, verified from block lower + valid.lower.

   Compact cells centered immediately before, at, and after the boundary match
   single-block coordinates, size (31) and source intensity for both overlaps.
   Extended cells fail: overlap 5 gives 233→202 pixels; overlap 32 gives 903→834.
   These components extend beyond the owning block's halo; overlap is shared
   between blocks, not the same amount of context on each side of a cell.

   Two competing seeds across the boundary retain correct output coordinates
   but fail size equivalence: single-block sizes 131/110 become 156/210 with
   overlap 5, and 241/241 with overlap 32. Cells.py filters halo seeds by valid
   ownership BEFORE shape segmentation, removing competing markers. A diagnostic
   wrapper keeps halo seeds during segmentation and filters output rows afterward:
   overlap 32 then matches 131/110 exactly. Overlap 5 still lacks enough context.
   This wrapper is experiment-only, not a production fix. Output row identity is
   compared by global seed coordinates; numeric labels are block-local, and
   stitched voxel-label equivalence has not been established by these tests.

   The first block report (review2-blocks-20261026T114031083768Z) used block-local
   valid.lower as if global and is superseded: its apparent passes were not a
   valid internal-boundary test. The corrected intermediate report ends 114113126407Z;
   the final report above adds the halo-competitor control.

Decision: retain only the equivalent speed shortcut in the experimental baseline.
Do not adopt the geodesic post-processing or automatic merge rule. Before any
production proposal, resolve overlap/ownership semantics (including truncated
components) and develop an orientation-invariant boundary policy with explicit
ambiguity handling. Biological QC and real 3D validation remain outstanding.

### Component segmentation validation — 2026-10-26

Scripts: validate_component_segmentation.py and check_component_pipeline.py.
Stage evidence: test-data/component-validation-20261026T112815693824Z/.
Full-detector evidence: test-data/component-pipeline-20261026T112902770129Z/.
The 6% shallow-dip merge was DISABLED. Direct categorical markers and connected
equal-plateau collapse were shared between both comparison arms; thresholds and
seed coordinates were fixed. Component segmentation used face connectivity,
signed floating-point negative intensities, masked local markers, bounding boxes,
and skipped unseeded components.

27 synthetic cases passed: twelve seeded random tied-intensity cases each in
2D and 3D, empty foreground, unseeded foreground, and diagonal-only contacts.
Checks covered seed preservation, allowed label IDs, no background leakage,
no cross-component labels, complete coverage of seeded components, repeatability,
padding invariance, C/Fortran memory layout, and no unrelated changes after
deleting a seed. These are computational properties, not biological accuracy.

Eight 256x256x1 demo crops were tested. Both original image-25 crops retained
identical arrays (24/18 accepted). In the six image-26 crops, four changed some
boundaries (39 pixels total across them). Three seeds crossed the 5-pixel cutoff:
- x800_y200 (92,166): 4→18 pixels, becomes accepted (crop total 27→28).
- x1400_y200 (246,46): 6→1 pixels, excluded (58→57).
- x1400_y450 (194,5): 5→4 pixels, excluded (36→35).
Other image-26 crop totals remain 0, 1 and 41. All before/after sizes are saved
in CSV files; boundary-review.png shows the three acceptance-change sites.
Visual inspection shows competing seeds still partition these objects; component
isolation stabilizes independence but does not resolve their biological counts.

Full ClearMap detector checks on all three crops with changed acceptance decisions
matched every stage-level coordinate and size exactly. Two full runs per crop
were identical, including source-intensity measurements. This used one worker,
one native thread, in-process experimental function replacement, and a single
Z block; it is not multi-block or full-brain pipeline validation.

Median segmentation time over three runs on seeded crops was about 1.3–10.6 ms
per entire 256×256 crop for the component method versus 0.7–1.2 ms per crop
globally (roughly 2–14x slower). Including the unseeded crop, the ranges were
0.28–10.63 ms versus 0.45–1.22 ms per crop. Absolute times
are tiny on these crops; do not extrapolate to whole brains. Peak memory and
real 3D throughput have not been measured.

Decision: component isolation is a supported experimental baseline for further QC,
not yet a production adoption. Next review the three altered decisions, then
validate representative real 3D volumes and block boundaries before reconsidering
automatic merging. No production source, installed package or thresholds changed.

### Nonlocal watershed investigation — 2026-10-26

Script: trace_watershed_locality.py. Completed evidence:
test-data/watershed-locality-20261026T081717859148Z/report.json and
synthetic-locality.png. Installed scikit-image version: 0.20.0.

Confirmed that the unexpected changes occur in foreground components disconnected
from every removed seed. Their images, masks and surviving marker IDs are identical.
The original baseline sizes reproduce exactly. In x1400_y200, removed seeds are
in components 116/118, but components 89/106/131 change. In x1400_y450 the removed
seed is in component 83, while component 89 changes. Thus foreground connections
between these regions do not explain the effect.

A minimal flat-image reproducer has two disconnected islands; removing the only
seed from the first island changes seven pixels between two fixed seeds in the
second island. This reproduces the problem without demo data or the merge rule.
The installed Python wrapper uses one global watershed queue; its documentation
describes intensity priority and entry-time tie handling. Giving every pixel a
unique sub-intensity priority eliminates unrelated changes in both demo crops.
Together these observations strongly implicate global queue tie handling. The
compiled queue's exact internal ordering was not instrumented in this test.

Signed floating-point negation gives exactly the same before/after results as
the existing unsigned negation on these masked demo inputs. Original marker-ID
preservation was already tested separately and also retained the effect.

Experimental workaround: label the threshold foreground with face connectivity,
then watershed each component separately in its bounding box using the same
marker IDs. This produced ZERO unrelated changed pixels in both crops and
preserved the synthetic second island. Component-wise sizes stayed 10→10, 1→1,
3→3, and 4→4 for the four previously affected seed coordinates. Some differ from
the old global baseline (10,6,3,5): stability does not establish more accurate
biological boundaries or preserve every previous acceptance decision.

Recommendation: validate component-isolated segmentation as a separate correction
before reassessing the 6% merge rule. Do not use intensity perturbation as a
production fix; it was a diagnostic and imposes arbitrary pixel ordering.
Remaining work includes regression checks, representative 3D/connectivity cases,
runtime/memory measurement, and full-pipeline validation. Neither component
isolation nor the merge rule has been adopted in the production detector.

### Frozen-rule challenge on fresh examples, 2026-10-26

Script challenge_shallow_dip.py; results and all six merge images:
test-data/dip-challenge-20261026T072421541529Z/.
Cutoff remained 6%; detection threshold 168. Six predefined non-overlapping
256x256 windows from image 26, frame 5/channel 0, were evaluated. These are fresh
to this rule evaluation, not an independent specimen or labelled accuracy set.

308 seeds became 302; accepted detections changed from 163 to 156. The six
proposed merges involve peaks 1.41–2.24 pixels apart, with region sizes:
case 1: 27+4 to 31; case 2: 7+62 to 69; case 3: 16+12 to 28;
case 4: 13+43 to 56; case 5: 39+12 to 51; case 6: 32+33 to 65.
All remain accepted after merging. Visually these are plausible compact-object
merges, but none has a new human label and accuracy is not established.

Five deliberately adversarial constructed-label cases exposed three overmerges
(long bright bridge, unequal peaks with shallow valley, and 3D axial bridge),
one remaining split (a single object with deeper texture), and one preserved
deep-valley unequal pair. These are stress tests of supplied seeds, not a
representative benchmark or full peak-detection validation. The failure counts
must not be presented as biological accuracy estimates.

Additional unexpected effects require investigation: five merges remove an
accepted seed and one removes an already rejected seed, explaining a decrease
of five, but total accepted detections decrease by seven. Surviving seeds in
x1400_y200 change sizes at (246,44):10 to3, (246,46):6 to1, and (247,45):3 to13;
in x1400_y450, (194,5) changes 5 to4. These are away from the merge centers.
trace_challenge_relabeling.py retained original marker IDs after deleting merged
seeds; the same acceptance changes persisted (fixed-id-trace.json). Therefore
sequential ID renumbering alone does not explain the effect. No cause has yet
been established; investigate watershed tie behavior and foreground connectivity.

Decision: do not promote the 6% rule to an unattended default. Keep it as a
reviewed experiment. Next isolate these additional watershed changes, then
review all six real merge candidates with the user. Broader safeguards require
evidence; adding a distance cutoff alone would not solve touching-cell ambiguity.

### Shallow-dip rule trial, 2026-10-26

Script: test_shallow_dip.py. Evidence:
test-data/shallow-dip-20261026T071149191769Z/report.json and comparison.png.
Starting with direct markers plus connected-plateau collapse, process seeds
strongest-first, breaking equal ties lexicographically. Suppress a candidate
only when a face-connected path above threshold 168 and at least
(1-fraction) times its peak reaches an already retained seed. This avoids
chaining suppression through discarded seeds. It uses no physical distance or
shape prior and remains experimental.

Tested fractions 0, 3, 5, 6, 10 and 15 percent. At 6 percent, the reviewed upper
object changes from regions of 24 and 17 pixels to one 41-pixel region. Its lower
neighbor stays one 55-pixel region, C stays one 8-pixel region, and the three
reviewed center objects retain their prior seeds and sizes. The only seed
suppressed across these two crops at 6 percent is the targeted duplicate.
Three stage-level seed/segmentation repetitions per crop/cutoff were identical.
At 3 or 5 percent the duplicate remains; 6 and 10 percent give the same crop
counts. At 15 percent another unreviewed center-crop merge appears.

Synthetic controls: a shallow ripple becomes one seed; deep-separated peaks and
touching unequal peaks with a deep valley retain two seeds. A deliberately
ambiguous two-object case with unequal peaks 400/240 and a bridge of 232 is
incorrectly merged if interpreted as two objects. This is a demonstrated
limitation, not a passed biological validation. Synthetic seeds were supplied
directly, so these controls test the merge stage, not peak-generation recall.

Conclusion: 6 percent is a useful candidate for further controlled review, not
a recommended universal default. It was selected using this tuning example.
Next assess fresh touching/unequal-brightness examples and representative 3D
data before production integration. Full-pipeline and held-out validation remain
outstanding. No source checkout or production settings changed; A/B remain
uncertain. Record all future merge proposals for separate subscription-agent QC and human review.

### Remaining double-peak investigation, 2026-10-26

Script: investigate_double_peak.py. Evidence:
test-data/double-peak-trace-20261026T070820249902Z/report.json and trace.png.
The reviewed upper right object has seeds P=(149,39) and Q=(151,38), both
background-corrected intensity 304. Their strongest four-connected path is
304,288,288,304: a dip of only 16 (5.3% of peak intensity). Exact connected
plateau collapse cannot join these seeds because the connecting pixels are
lower than the peaks. Equal maxima both survive the maximum filter.

As a contrast, the nearby lower object has a peak at (163,51), intensity 400.
Even the strongest path anywhere within the full crop from P to this neighbor
falls to 32, a dip of 272 below the smaller peak. It is disconnected from the
upper object at the current threshold 168. The path algorithm maximizes the
minimum intensity, then chooses a shortest path at that level; paths have
different lengths, shown with normalized distance in the figure.

This supports testing a shallow-valley/prominence rule, rather than merging
all nearby peaks or all touching foreground. It does not establish a universal
merge threshold or validate behavior on truly touching cells. No merge rule,
threshold, source checkout or production settings were changed in this trace.
Next controlled experiment should vary the allowed dip and include synthetic
shallow double peaks, two deep-separated peaks, and touching unequal peaks,
plus the existing human-reviewed objects. Keep uncertain A/B out of tuning.

- Retain direct categorical markers and connected-plateau collapse as candidate
  code improvements, with separate tests and documented scope.
- Next investigate the remaining disconnected peaks on the reviewed upper
  object, including intensity between peaks. Any broader merge rule must also
  preserve demonstrably separate neighbors; do not merge merely by proximity.
- Before promotion into ClearMap-work: test the combined full pipeline, broader
  synthetic cases, representative 3D data and held-out human-reviewed examples.
- Tune intensity/size settings only after correcting these marker/peak defects.
  Do not optimize against uncertain A/B labels or claim accuracy from tuning crops.
- Later agent integration should retain run manifests, reproducible settings,
  review images, human approval/uncertainty records, and safe stop/resume behavior.

## Workspace correction — 2026-10-26

The user clarified that iDisco-analysis is for analysis only. All detector
improvement scripts, review notes and experiment outputs were moved to
C:\dev\ClearMap-work\experiments\detector-quality on codex/work. Two demo TIFFs
were copied and hash-verified, preserving the original analysis inputs. The
scripts now resolve their working root from their own location. Historical
references to iDisco-analysis describe the previous location only. Future
ClearMap improvement work belongs in ClearMap-work. All 261 moved file hashes
were verified before path edits; see migration-original-hashes.json.
The eventual target remains automation of the entire pipeline with a separate
subscription-agent QC review and human QC checkpoints, not detection-only automation.

### 2026-10-27: joint review of Kenny's preliminary R1 marks
- Read exported labels from Downloads/public-cellfinder-reference-labels.json: 2 object, 2 uncertain, 4 artifact; all regions incomplete. Source annotations remain unchanged.
- Created test-data/reference-review-v1/pair-z12-23.png from raw signal, fixed display range 52..1005, including context outside the review crop. Cyan cross is global XY (154,149), shared by object Z18 and uncertain Z20.
- Visual interpretation: bright structure persists near the marked XY through neighboring planes, with no clear separation between Z18 and Z20. Provisional same-structure hypothesis; insufficient evidence for two separate cells. Axial persistence/elongation and surrounding intensity changes prevent confident biological identity from this montage alone. No label adjudication or accuracy scoring performed; awaiting joint review.

### 2026-10-27: second joint-review candidate
- User clarified the Z20 uncertain mark questions cell identity of the same candidate; working adjudication is one candidate with uncertain identity, preserving original export.
- Rendered object-z3-14.png around global XYZ (139,156,9), fixed display 52..1005 and wider raw context; orange line indicates R1 upper Y boundary at global Y160.
- The second candidate is compact/rounded near Z7-9 but persists and changes shape through adjacent planes, reaching/crossing the review-window boundary. Provisional edge-affected candidate with uncertain biological identity; no confirmed positive label assigned.
- Broad brightness change between Z9 and Z10 is visible under fixed display settings, also previously visible at Z19/20. Cause is unverified; do not interpret the brightness change as object termination or biological activity. Further source/plane continuity checks are warranted before treating axial morphology as decisive.
- No production changes, threshold changes, or accuracy scores.

### 2026-10-27: human-confirmed provisional review decisions
- Kenny accepted the recommendation for R1 local XYZ (43,60,9), global (139,156,9): edge-affected candidate with uncertain biological cell identity. Kenny confirmed the initial object judgment relied mainly on the rounded appearance at Z9.
- Preserve this as an uncertain candidate with an edge flag, not a confirmed cell or confirmed artifact. Exclude it from confirmed-cell accuracy scoring pending adjudication; retain it in uncertainty reporting.
- The original exported annotation file remains unchanged. Together with the earlier XY (58,53), Z18/Z20 identity clarification, neither of the two initially object-labeled candidates is currently a confirmed biological positive. This does not establish absence of cells in R1; review is incomplete.
- Next prerequisite: investigate the visible broad intensity transitions at Z9/10 and Z19/20 and source plane continuity before using axial shape as decisive evidence.

### 2026-10-27: raw plane continuity audit
- Added audit_public_plane_continuity.py; report test-data/reference-review-v1/plane-continuity-audit.json. All 60 TIFF SHA256 hashes match the download manifest; both NPY arrays equal their TIFF planes exactly.
- Signal full-plane medians Z9/10: 233 -> 150 (-35.6%); Z19/20: 247 -> 149 (-39.7%). Background: 231 -> 130 (-43.7%), 245 -> 129 (-47.3%). Repeated rising intensity within each ten-plane span is present in source pixels, not per-frame viewer contrast.
- Signal adjacent-plane correlations at these boundaries: 0.696 and 0.802; other adjacent pairs range about 0.856-0.941. Correlation alone does not prove spatial continuity or its absence.
- Embedded signal source labels run consecutively CT_BY_70_2_01270_ch00.tif through 01299. Pinned official cellfinder/napari/sample_data.py fetched directly confirms numeric 0..29 stacking for both channels. No evidence of local ordering error; acquisition/processing cause remains unverified because TIFF metadata lacks acquisition details.
- Implication: retain sample for computational stress tests and provisional review practice; do not use it to establish biological accuracy or rely on axial apparent shape/intensity termination for confident cell labels. Existing uncertainty decisions preserved. No normalization, production or threshold changes.

### 2026-10-27: better documented biological validation candidates
- User accepted retaining current cellfinder demo for computational checks rather than biological accuracy validation.
- Primary-source search identifies DELiVR c-Fos as preferred initial candidate: https://pmc.ncbi.nlm.nih.gov/articles/PMC11239522/ documents 48 annotated 100-cubed patches, 5889 cells, expert-biologist vetting, 39/9 train/test split, and acquisition XY1.625um/Z6um. Patch headers/resampling and downloadable annotation format still require verification. Data links: https://github.com/erturklab/delivr_train and delivr_cfos. Patches derive from one brain, so not independent-brain validation.
- SELMA3D official data page https://selma3d.grand-challenge.org/data/ supplies annotated patches via BioStudies S-BIAD1196 and cites DELiVR; do not assume independent data or count touching binary-mask components as verified cell instances.
- CANVAS author paper https://arxiv.org/html/2603.29842v1 documents cFos and five other markers, cell centroids, manual false-negative recovery, and train/test ROIs. Portal https://canvas.lightsheetdata.com . Promising count-oriented complementary benchmark; downloadable subset access and protocol differences require audit.
- Recommendation: first audit a small DELiVR c-Fos raw/annotation subset, preserve published split, verify axes/physical spacing/mask semantics/plane continuity, then establish one-to-one object metrics before tuning. No new datasets downloaded, no production changes, no biological accuracy claims.

### 2026-10-27: DELiVR step 1 audit; data gate not yet passed
- Agreed five-step milestone order recorded in DELIVR_DATA_AUDIT.md. Start with data audit; baseline only after prerequisites pass, then held-out comparison, human adoption review, workflow packaging, server parity.
- Downloaded two pinned official raw/gt pairs (~4.4MB), verified Git blob integrity, saved SHA256 and metadata/continuity report. Added reproducible audit_delivr_subset.py.
- Both 100-cubed exports have unknown physical units and unit zooms; published acquisition spacing cannot yet be asserted for exported patches. Both masks binary, not individual-cell IDs. Connected-component counts vary by connectivity and are not accepted cell counts.
- Visually confirmed an abrupt spatial-pattern transition at array-axis2 indices10/11 in patch1008_0 (correlation -0.062). Cause unresolved. Patch1147_0 worst adjacent correlation0.554. No duplicate adjacent planes in either patch.
- Inventory48 raw/41gt, seven missing gt partners; inspected official training code/config does not identify the paper's nine test patches. All downloaded data quarantined for QA only, no train/test assignment invented. No detector execution or thresholds changed.
- Details, remaining provenance questions, exact evidence paths and next prerequisites: DELIVR_DATA_AUDIT.md.

### 2026-10-27: DELiVR archived provenance follow-up
- Publication v1.0.0 cFos inventory has89 blobs identical to current files; 48raw/41gt discrepancy persists in the archived release. Training v1.0.1 tree does not include a named test manifest.
- Published scoring code intentionally constructs reference instances from binary connected components. Its overlap matching is not one-to-one; duplicate predictions can each earn TP against the same reference. Preserve this distinction from our planned count-accuracy metrics.
- Supplementary PDF inaccessible through attempted routes; its contents remain unverified. Drafted DELIVR_AUTHOR_QUESTIONS.md, not sent, covering split/calibration/instance references/axis2 discontinuity. Updated DELIVR_DATA_AUDIT.md with evidence. No detector execution or tuning.

### 2026-10-27: CANVAS access audit and DELiVR sending authorization
- User authorized sending the prepared DELiVR request. No email connector available; asked which email service/account to use. Not sent yet.
- CANVAS documentation/live portal inspected: documented XYZ1.8/1.8/4um; centroid CSVs; cFos TRAIN3ROIs9390cells, official TEST10619cells withheld. SHIELD/SmartSPIM rather than protocol-matched iDISCO.
- Data portal's binding license restricts derivative software/models/results and prohibits Production Systems deployment; no download or agreement acceptance. Full details in CANVAS_DATA_AUDIT.md. This materially affects suitability for the planned server pipeline and needs clarification before dataset use.

### CANVAS first subset acquired and inspected
- User-confirmed registration succeeded; downloaded TRAIN region2 annotations and three adjacent planes, ~202MB total. Official TEST left unopened.
-2827 unique reference coordinates/IDs; plausible visual overlays. Some labels extend beyond nominal half-open ROI boundaries; preserve them pending convention audit.
- TIFF units absent; calibration sourced from paper. Three-plane crop intensity/continuity looks consistent (medians345/346/346, correlations0.881/0.892), with limited scope. No biological accuracy claim or detector run. Evidence in CANVAS_DATA_AUDIT.md and test-data/canvas-audit/audit.json.

### 2026-10-30: expanded CANVAS continuity audit completed
- All12 planes1130..1141 decoded; 340x340XY crop includes20-pixel context. Medians342..347 and adjacent correlations0.853..0.891, visually coherent in expanded-alignment.png.
-138-center +/-1 voxel diagnostic gives median631 unchanged versus633 at best alternative; insufficient evidence to shift labels. Source coordinates preserved.
-40 nominal boundary exceptions retained:39 upper-bound and1 lowerX-1. Future scoring must declare interior/core and ambiguity treatment, not silently drop references or mark unlabeled context negative.
- Data audit progressed;12planes do not yet validate detector preprocessing halo or full3D cell extent. No baseline accuracy claims or detector run. See CANVAS_DATA_AUDIT.md.

### 2026-10-30: fixed-core CANVAS context challenge FAILED
- Added test_canvas_context.py. Predeclared half-open global core XYZ[4422,3218,1134)..[4682,3478,1138),260x260x4 voxels. Reference labels not used to select detector parameters or evaluate biological accuracy.
- Original installed ClearMap algorithms, controlled single native thread, earlier frozen experiment configuration: background21x21, maxima11x11x1 threshold168, shape threshold168, illumination/equalization/DoG off; single processing block. This is NOT stock-default configuration and NOT experimental corrected segmentation.
- Final report test-data/canvas-context-20261030T071132877319Z/report.json; plan and all core candidate CSVs saved beside it. Context XY/Z10/1,20/2,40/4 gives823/832/827 returned candidates; legacy size5..500 counts477/474/464. These are algorithm outputs, not confirmed cells.
- Fixed XY40, increase Z halo1/2/3/4 gives830/827/827/827 returned candidates. Equal totals conceal changed identities: each adjacent depth comparison has825 common coordinates. Common-coordinate size changes365/279/247; size-filter counts467/470/463/464. Therefore depth-context invariance fails even where totals match.
- Largest context exact repeat passes coordinates, size and intensity. Reproducibility does not establish context invariance.
- No sufficient halo declared, no accuracy score produced. Original known marker/segmentation issues may contribute; cannot attribute every change solely to insufficient overlap. Next isolate preprocessing/peak outputs from segmentation before selecting extra download depth or promoting any correction. Production source/thresholds unchanged.

### 2026-10-30 — CANVAS context changes isolated by stage

- Added experimental `test_canvas_stages.py`; production source and thresholds unchanged. Evidence: `test-data/canvas-stages-20261030T071858509393Z/report.json`, per-context core CSVs and compressed core stage arrays. Earlier `071819388771Z` is superseded: it used NumPy seed ordering instead of native `Cells.ap.where(..., processes=1)` and counted background label zero as boundary-touching.
- Fixed core XYZ [4422,3218,1134) to [4682,3478,1138), XY halo40, Z halos1/2/3/4; same audited 12-plane source and frozen Disk21 background / maxima11x11x1 / threshold168 configuration. No plateau collapse or merging. All variants receive identical native-ordered seeds within each context, one native thread.
- Corrected core intensities and raw maxima masks are EXACTLY identical across all three increases: zero changed voxels, 848 identical core peak coordinates. Thus these depth-dependent differences originate after peak detection in this experiment.
- Native segmentation retains 830/827/827/827 core candidates; direct global and direct per-component variants retain835 throughout. Thirteen raw peaks lie outside the strict >168 segmentation foreground; raw peaks must not be called cells.
- Size changes across Z1->2 / Z2->3 / Z3->4: native372/283/251; direct global211/125/68; direct component210/125/66. Among peaks in components enclosed at BOTH depths: native60/63/78 size changes, both direct variants ZERO. This supports a native marker/segmentation artifact independent of missing component context; it is not proof of biological correctness or an exhaustive diagnosis of each native failure.
- At halo4, 481 core peaks still belong to foreground components touching an artificial Z face (peak count, NOT distinct component count). Direct-component segmentation still has66 size changes and401 changed core assignment voxels from halo3 to4. Added depth remains relevant to these incomplete components; context convergence has not passed.
- This is a stage-level comparison, not a replacement end-to-end baseline: native retained counts reproduce the preceding context run, but size-change totals differ slightly (372/283/251 versus365/279/247). Preserve that distinction and reconcile stage plumbing before claiming exact full-pipeline size parity.
- Next: obtain a bounded additional depth window around the SAME core, rerun the isolated stages, and require both enclosed component support and stable coordinate-mapped assignments/sizes. Keep unresolved components as needs_context; do not promote segmentation corrections or report biological accuracy yet. Annotation labels and published TEST split remain unused.

### 2026-10-30 — Same-core depth extension to 20 planes

- Downloaded eight additional image planes from the already authorized CANVAS image source; prefixes1126..1145 now contiguous. No annotations or official TEST accessed. `audit_canvas_depth.py` verifies all20 decode as uint16 YX10258x5599, records local SHA256 hashes, and asserts original12 cropped planes are pixel-identical. Evidence `test-data/canvas-audit/depth20-audit.json`; crop `depth20-zyx.npy`, origin XYZ4382,3178,1126, shape ZYX20x340x340. Adjacent crop correlations0.838..0.891; medians349..340. These descriptive checks support continuity, not biological validation or calibrated TIFF spacing.
- Same half-open scoring core lower[4422,3218,1134], upper[4682,3478,1138], unchanged XYhalo40 and all stage parameters. `CANVAS_DEPTH20=1` selects Zhalos4,6,8,8(repeat) in `test_canvas_stages.py`. Evidence `test-data/canvas-stages-20261030T074022793575Z/` contains pre-run plan, report, core stage arrays and tables. Halo4 core table reproduces the previous native-ordered experiment exactly.
- Preprocessing and raw maxima: ZERO changed core voxels across every comparison;848 identical core peaks. Native retained counts827/829/827; direct variants835 throughout. These are algorithmic candidates, not biological cell counts.
- Halo4->6: size changes native231 / direct global39 / direct component34. Enclosed-at-both-contexts size changes84 / 2 / 0 respectively. Core assignment voxel changes1278 /198 /171.
- Halo6->8: size changes native225 / direct global9 / direct component7. Enclosed-at-both-contexts size changes123 /2 /0 respectively. Core assignment voxel changes1167 /27 /16.
- Boundary support: core peaks in artificial-face-touching components481->352->280; distinct such foreground components145->108->84. All these boundary contacts include Z faces. Do not equate peak count with component count. At largest context,280 peaks still require context despite many unchanged sizes.
- Largest-context repeat: ZERO preprocessing, maxima, size or core assignment changes for every variant. Reproducibility passes; depth convergence DOES NOT yet pass.
- Interpretation: more depth substantially reduces experimental component-segmentation sensitivity, but native marker artifacts remain and direct global watershed exhibits enclosed-component sensitivity. Per-component isolation removes enclosed-component size changes in this challenge; this is not production adoption, full-mask equivalence, or biological accuracy. Keep unresolved boundary components marked needs_context. Next bounded extension can target larger Z margins around the same core; retain stage separation and a hard context budget.
- No production source, thresholds, reference labels or published split changed.

### 2026-10-30 — Trace seven remaining component-segmentation size changes

- Added `trace_canvas_depth_changes.py`. Final evidence `test-data/canvas-trace-20261030T074555869523Z/report.json` and `review.html` with seven local XY/XZ comparison images. Supersedes preliminary trace074517507006Z by adding an exact pairwise transfer assertion. No production or threshold changes, annotation access, or biological scoring.
- Recomputed halo6/8 direct-component masks using native-ordered raw maxima. Asserted all shared corrected voxels equal and all seven sizes reproduce the prior stage experiment. Controlled counterfactual: segment the larger volume with ONLY the original halo6 seeds, preserving their order/coordinates. This separates added image support from effects of the additional seed set, though it does not distinguish geometric competition from tied watershed queue behavior.
- Objects1/4/5/6/7: size198->199 /550->556 /442->460 /576->584 /788->797. Their changes reproduce exactly with larger support and original seeds; newly added seeds have zero additional mask effect for these objects. Objects1/4/6/7 only gain voxels outside the original volume. Object5 gains20 and loses2 voxels, with2 changed voxels inside shared support: added support can also change an internal boundary.
- Objects2/3: seeds[4493,3382,1134] and[4494,3381,1134], sizes22->8 and3->17. Fixed-original-seed larger-context counterfactual preserves22 and3 with identical masks. Adding newly visible seeds transfers EXACTLY the same14 voxels from object2 to3; pair union is unchanged. Their connected region has16->18 seeds. This isolates seed-set sensitivity, not a proven biological merge or confirmed tie-break cause.
- All seven remain in connected foreground regions touching at least one artificial Z face at halo8. They represent five distinct connected regions (2/3 share one,6/7 share one). Thus retain needs_context, even for the pair whose union is stable.
- Visual check of object2 PNG confirms the intended overlays and visible boundary redistribution; raw local projections may superpose unrelated structures and are not biological labels. Review all cases before cell identity judgments.
- Next targeted experiment: isolate the2/3 shared component and add the two new seeds individually while keeping support fixed; test seed-ID/order and orientation sensitivity to discriminate legitimate competition from watershed tie behavior. Continue bounded context expansion for the other incomplete regions. Do not merge the pair automatically.

### 2026-10-30 — Individual added seeds and watershed orientation challenge

- Added `test_canvas_seed_competition.py`; evidence `test-data/canvas-seed-competition-20261030T085842709966Z/report.json` and `component.npz`. Fixed the larger halo8 corrected image and exact shared foreground component; reused16 original seeds and added the two newly visible seeds individually or together. Stable categorical seed IDs, no merging or threshold/source changes.
- New A XYZ[4494,3381,1126]; new B[4496,3380,1127]. Original pair XYZ[4493,3382,1134] /[4494,3381,1134]. Pair sizes: old-only22/3; +A8/17; +B22/3; +both8/17. Reproduces the prior trace exactly. A triggers the exact14-voxel transfer; neither new seed receives any of these14 voxels.
- Tested all48 axis permutations/reflections with image, mask and markers transformed together and output inverse-mapped. Pair mask differs from canonical orientation in28/48 old-only,17/48 +A,29/48 +B,21/48 +both cases. Every case has both possible pair-size outcomes22/3 and8/17. Whole-component orientation failures37/48,30/48,35/48,33/48 respectively. These counts include the unchanged identity orientation in denominators; geometric transforms do not add biological information.
- Repeat runs exact for all4 cases; reversing numeric seed IDs and mapping them back changes ZERO component voxels. Numeric ID ordering is not the trigger in this control. Spatial traversal/queue ordering remains implicated; this is not a direct instrumentation of the watershed priority queue.
- Conclusion: seed A toggles an orientation-sensitive allocation already present with the original seed set. This is strong evidence for algorithmic watershed tie/traversal sensitivity rather than an unambiguous biological competitor stealing the14 voxels. The transferred region spans13 distinct corrected intensities178..397, so do not misdescribe it as one flat14-voxel intensity plateau. Basin ties can propagate beyond a flat saddle.
- No automatic merge and no production adoption. Component remains needs_context. Next diagnostic: inspect the pair's seed heights and connecting saddle, then challenge a deterministic spatially symmetric tie policy (including an explicit ambiguous-voxel option) against these saved transforms and prior failure examples. The earlier geodesic prototype was not validated; do not assume it is a solution.

### 2026-10-30 — Saddle and ambiguity-preserving policy diagnostic

- Added experimental `test_canvas_saddle_policy.py`; final evidence `test-data/canvas-saddle-20261030T123327085483Z/report.json` and per-case labels/ambiguity arrays. No merging, production edits, threshold tuning or biological inference.
- Pair peaks both425 corrected intensity; maximum-bottleneck face-connected saddle415. Independently asserted seeds share a connected region at >=415 and separate at >415. Relative dip10/425=2.35%, descriptive only, NOT a merge criterion.
- Tested a conservative maximin-connectivity policy: independently compute each seed's best minimum path intensity; assign unique highest-score winner, explicitly flag equal-score voxels ambiguous, preserve seed identity. No spatial order/seed-ID tie-break. This is a distinct segmentation objective, not a patch proven equivalent to watershed. It avoids dependence on the failed earlier plateau-only reassignment prototype.
- All48 axis permutations/reflections pass exact label AND ambiguity-map invariance for each of4 seed configurations (192 checks). Reverse numeric-label control passes; foreground coverage as assigned-or-ambiguous and seed retention assertions pass. Flat symmetric3D synthetic test flags all25 nonseed voxels ambiguous and preserves2 seeds.
- All14 disputed transfer voxels ambiguous in every configuration. However408/407/404/403 of431 foreground voxels are ambiguous for old-only/+A/+B/+both; pair uniquely assigned sizes1/1 in all cases. The policy is far too conservative for routine size measurement; computational consistency does not establish useful or biologically accurate segmentation.
- Preliminary123207542176Z had saddle intensities offset by-65536 from converting saved unsigned-negated watershed input before reversing the negation. Superseded and corrected by recovering uint16 intensities first; labels were unaffected by the constant offset. Intermediate123242001580Z has corrected results; final run adds independent threshold-connectivity assertions.
- Recommendation: retain this as an uncertainty diagnostic, not production. A next experimental secondary distance criterion must use physically meaningful axis spacing and preserve equal-distance ambiguity, then pass the same transforms and prior failure examples. Do not adopt the previous failed geodesic implementation or infer one biological cell from the shallow saddle. Region remains needs_context.

### 2026-10-30 — Physical mask-geodesic secondary assignment

- Added experimental `test_canvas_physical_ties.py`; evidence `test-data/canvas-physical-ties-20261030T132032079740Z/report.json` and per-case label/ambiguity arrays. Production code, thresholds and seed set generation unchanged; no merging.
- Primary objective unchanged from the conservative diagnostic: maximize minimum path intensity independently per seed. Among equal-primary-score seeds, minimize shortest face-connected foreground-mask path length using paper XYZ spacing1.8/1.8/4um. Exact integer steps18/18/40 in0.1um units avoid floating-point tie tolerances. Distances are through the entire foreground mask, not restricted to paths achieving the primary bottleneck; this explicit objective differs from watershed and from shortest widest-path optimization. TIFF calibration remains unverified.
- All192 orientation checks (48 per old-only/+A/+B/+both) pass exact labels and ambiguity maps, with spacing permuted alongside axes. Reverse numeric-label checks and seed retention/coverage assertions pass. Synthetic tests preserve the exact9-voxel equidistant plane and distinguish a1.8um X step from a4um Z step (unit-spacing control restores the expected tie).
- Ambiguity falls from408/407/404/403 to38/431 voxels in every configuration. Pair assigned sizes13/15 in all4 cases. Additional full-mask comparison verifies both pair memberships unchanged under either/both added seeds, not merely equal sizes.
- Of the original14 transfer voxels,8 remain ambiguous and6 are assigned to existing seed ID10; neither original pair seed receives these14 under the new objective. This is a substantial reassignment to a third seed, not a validated choice between old watershed outcomes22/3 and8/17. Requires biological and spatial review before adoption.
- Result: promising computational invariance on this one fixed connected region, not detector-wide or biological validation. Needs context persists at the artificial Z boundary. Next review third-seed ownership visually and challenge this policy on earlier tied examples, complete components, and distinct neighboring cells before any production proposal.

### 2026-10-30 — Third-seed inspection and additional-region challenge

- Added `challenge_physical_ties.py`; completed evidence `test-data/physical-ties-challenge-20261030T133638544441Z/report.json`, saved region arrays and `third-seed.png`. Initial run aborted on zero eligible demo25 components; final selection reports found counts rather than silently substituting cases. Final report additionally records baseline-connectivity checks computed from saved arrays; script includes those checks for reproducibility.
- Third seed ID10 at XYZ[4495,3381,1135], corrected height432, assigned27 voxels. Six transferred voxels all at Z1135, physically nearer this seed than the eligible original pair (distances5.4..9.0um versus7.6..11.2um), and all remain face-connected to seed10 in its assignment. Exact per-voxel eligible seeds/distances saved. Viewed XY evidence: nearby peaks on adjacent planes within bright structure; neither independent cells nor one-cell identity established.
- Deterministic bounded challenge selects first4 closed CANVAS components with30..700 voxels and2..8 raw peaks, then up to2 eligible components from each earlier demo25/26 crop. Demo uses earlier plateau collapse and unit-grid 2D algorithmic distance, not assumed physical calibration. Found4 CANVAS,0 demo25,2 demo26. These are components from previously used demo crops, not a complete rerun of every historical failure case. No reference labels used.
- Including original region,7 regions pass all48 orientations each (336 exact label/ambiguity tests); seed retention passes. However policy creates detached seed-owned islands in original region(1 voxel) and ALL4 new closed CANVAS regions(3,15,2,13 voxels respectively). Corresponding component-watershed baselines have ZERO detached assignments for every seed in all7 regions. Two demo26 regions have none under either method; one marks17/31 voxels ambiguous.
- This is a substantive policy failure despite orientation stability: independent per-seed intensity/distance objectives do not guarantee a connected territory rooted at the seed. Reject this candidate for production segmentation/size measurement. A spatially sensible third-seed reassignment does not rescue the broader rule.
- Next proposal: preserve an explicit uncertainty flag for disputed assignments while testing a connected seeded-flood policy with symmetric handling of ties; do not silently reattach/drop islands or merge seeds. Review the failure cases before another algorithm change. Original pair still needs_context. No production changes or biological accuracy claims.

### 2026-11-02 — Connected seeded-flood diagnostic

- Added experimental `test_connected_seed_flood.py`; evidence `test-data/connected-flood-20261102T080908605748Z/report.json` and per-region labels/tied/unreached arrays. No production source, thresholds, merging, or reference labels changed.
- New objective explicitly differs from watershed and earlier independent per-seed maximin policy. Multi-source connected flood uses positive additive edge cost: integer axis distance * (1 + current component maximum corrected intensity - minimum endpoint intensity). Physical steps18/18/40 for CANVAS; unit-grid demo controls. Equal-cost proposals from distinct seeds are resolved simultaneously as uncertain boundary voxels, never by queue/coordinate/ID order. Ties do not propagate; any unreachable remainder is separately flagged. Every accepted assignment extends an already connected same-seed territory.
- Saved challenge: original pair region,4 closed CANVAS regions and2 demo26 regions. All336 orientation checks pass exact label/tie/unreached comparisons with spacing transformed alongside axes. Numeric label reversal and repeat controls pass. Assertions verify seed retention, assigned-or-uncertain coverage and ZERO detached voxels for every seed in all7 cases; prior independent-distance policy failed connectivity on5 of these.
- Tied counts: original4/431; CANVAS0/116,0/108,0/120,0/173; demo0/43 and3/31. No unreachable voxels in these cases. Symmetric synthetic flat region retains the expected15-voxel tie plane; single-seed control fills the full connected mask.
- Original pair sizes17/24 and exact pair masks unchanged for old-only/+A/+B/+both. Orientation tests cover all-seed configurations per saved region; ablation masks were compared in canonical orientation only in this run. Do not overstate ablation orientation coverage.
- Changed labels versus component watershed:214/431,40/116,33/108,43/120,71/173,1/43,9/31. Passing computational invariants does not establish biological accuracy; fewer ties alone is not proof of improvement. Edge cost intensity weighting is a new, untuned experimental choice. Component-maximum normalization may itself introduce context sensitivity when added context changes that maximum; context qualification has NOT been rerun for this candidate.
- Next: visually compare the connected-flood boundaries against watershed, then challenge larger context, stronger remote peaks, seed ablations under transforms, and cases where blocked ties leave unreachable foreground. Retain needs_context for the original boundary-touching component. No production adoption.

### 2026-11-02 — Connected-flood visual and context stress review

- Added `review_connected_context.py`; evidence `test-data/connected-context-20261102T081140385101Z/report.json`, `boundary-review.png`, boosted assignment arrays. Added optional diagnostic ceiling override to experimental flood only; default behavior unchanged. No production/threshold changes or merging.
- Viewed exact XY slices Z1134/1135 comparing component watershed, connected flood and4x remote-peak boost. Same corrected-image display window across panels; only seeds8/9/10 colored, others uncolored, ties yellow. Connected flood expands cyan/magenta territories at1134 and third-seed green territory at1135; displayed masks remain continuous. Visual comparison does NOT establish biological boundaries or whether these seeds are separate cells.
- Same scoring Z core1134..1138: trimming the saved halo8 foreground component to halo4 [1130,1142) and halo6 [1128,1144) yields ZERO changed core labels, ties or pair memberships relative to halo8. All have ceiling550. Scope is the previously saved component, not full detector/preprocessing rerun, not a new download, and not full-volume/context sufficiency validation. Original component still touches artificial boundaries.
- Fixed-mask/fixed-seed synthetic intensity challenge: raise existing seed17 to2x or4x component maximum. Assignments change14 or17 voxels respectively; pair8/9 membership and tied map remain unchanged. Each result is reproduced EXACTLY by leaving the image unchanged and raising only the global ceiling used in edge costs. Thus component-wide normalization is sufficient to explain this response; the test does not show the new intensity attracting those voxels directly.
- Connectivity assertions pass for cropped and boosted runs. Candidate is not ready for adoption: orientation and selected-core depth stability coexist with remote-intensity normalization sensitivity.
- Next proposal: remove dependence on the current component maximum in an experimental cost definition, predeclare its intensity scale, then rerun these same normalization, orientation, connectivity and depth challenges. Any new intensity weighting remains a methodological choice requiring review and biological validation; do not silently tune detector thresholds.

### 2026-11-02 — Local-gradient connected flood, predeclared cost

- Added `test_local_cost_flood.py`, reusing frozen region/context harnesses with experimental cost option in `test_connected_seed_flood.py`. Plan written before runs; evidence `test-data/local-cost-20261102T133214688138Z/plan.json`, `regions/report.json`, `context/report.json`, per-region arrays and `context/boundary-review.png`. Production code, detector thresholds and seed merging unchanged.
- Cost = integer physical axis distance * (1 + absolute neighboring corrected-intensity difference). No component maximum used in the edge cost. Gradient coefficient fixed at1 before results; no parameter search. This is a new intensity-gradient objective, not watershed-equivalent or intensity-scale invariant.
- Same7 saved regions: all336 orientation checks pass, zero detached voxels, no unreachable foreground; seed retention, repeat, numeric-label reversal and symmetric/single-seed synthetic controls pass. Tied voxels4 in original region and2 in demo26_30; zero in other5. Original pair21/20 voxels, exact masks unchanged under +A/+B/+both.
- Same saved-component depth tests at margins4/6 versus8: zero changed core labels/ties/pair memberships. Scope remains limited to this saved component with fixed preprocessed image and markers, not a fresh full detector or proof of sufficient acquisition depth.
- Global-ceiling-only controls2x/4x now change ZERO labels, as expected because ceiling is unused. Actual synthetic seed17 boosts2x/4x each change2 assignments, no pair or tie changes. Both changed voxels are4.0 and5.8um face-distance from seed17, labels17->1; increasing the local gradient makes escape from the brightened seed more expensive. This is an explainable local response, not proof of biological validity or immunity to all remote effects.
- Viewed exact-slice boundary comparison. New assignments substantially differ from watershed:331/431 in original,61/116,73/108,60/120,127/173 across CANVAS controls,1/43 and9/31 in demo controls. Do not interpret computational stability as superiority. The stronger-peak perturbation leaves displayed pair masks unchanged.
- Candidate remains experimental. Next priority is biological boundary review on complete, independently labeled objects plus fresh computational cases; the current set has been reused during method development and is not held-out evaluation. Original component remains needs_context; published TEST split untouched. No production adoption.
