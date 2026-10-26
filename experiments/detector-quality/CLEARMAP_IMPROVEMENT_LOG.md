# ClearMap improvement log

## Purpose and working agreement

Build a locally tested ClearMap improvement branch from controlled demo
experiments, then validate on representative data before remote use. The eventual
goal is an agent integrated into ClearMap: it runs analysis, presents evidence,
records decisions, and pauses at human scientific review checkpoints. No agent
integration or production detector changes have been implemented yet.

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
per component versus 0.7–1.2 ms globally (roughly 2–14x slower). Absolute times
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
uncertain. Record all future merge proposals for Astra QC and human review.

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
Astra QC review and human QC checkpoints, not detection-only automation.
