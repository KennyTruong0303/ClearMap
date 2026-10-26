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
