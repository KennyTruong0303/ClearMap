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

### Shallow-dip rule versus built-in h_max, 2026-10-29

Script: compare_dip_vs_hmax.py (seed stage only, ClearMap's own find_maxima).
Synthetic scenes, 200 per regime, ~7,300 scorable cells each; no real crops yet.
Run it on the saved crops with --crop <center|right>.npy --region <center|right>.

The h_max path as shipped has four defects: find_center_of_maxima drops the last
label (np.arange(1, n_label)); uint16 input wraps in source - h_max and raises;
face-connected labelling splits flattened plateaus and adds seeds (+1.4 per 100
cells at h=17 where the baseline adds none); and lowering peaks by h while a
brighter neighbour's slope stays unchanged lets the 11x11 window drop dim cells.

With 16-step intensities (all quoted NEATmap values are multiples of 16), the
baseline gives about 1 duplicate seed per 100 cells. A 10% dip removes nearly all
of them with no added lost cells; 6% removes about half. h_max with labelling
fixed also removes them but loses 0.2-1.0 more cells per 100, rising with h.
With continuous intensities it lost slightly fewer than the baseline (0.72
against 0.88 per 100), so the h_max losses are tied to the 16-step data.
The scenes lack bright bridges, so the dip rule's known overmerges are not
exercised; Codex's adversarial profiles still show them. Neither rule is ready
to adopt.

Tie-breaking and dog_filter (same benchmark; maxima found on the filtered
image, threshold 168 kept on the background-corrected image):
- A pure tie-break (under 0.5 units of a sigma-1 smoothed signal added) removes
  every duplicate, confirming ties as their cause. It raises lost cells from
  0.38 to 0.89 per 100, the continuous-data level (0.88): ties were also
  rescuing dim cells that the 11x11 window suppresses next to brighter
  neighbours, as in the 320/320 example.
- Cells.dog_filter with shape (7, 7, 1) and default sigmas gives 0 duplicates
  and 0.36 lost (additive, 16-step) and 0.32 lost (continuous, baseline 0.88),
  but 0.83 lost under strong texture, where the 10% dip rule loses 0.31.
  Shapes 5 and 9 were worse. The DoG output is not in intensity units, so a
  real run needs its own threshold; test on the saved crops before adopting.

Anisotropic 3D (--dims 3), 2026-10-30: 96x96x24 volumes, 2x2x5 um voxels, 150
cells per volume (about 34,000 per mm^3), cells round in micrometres, 40 scenes
per regime, ~5,600 scorable cells each. A cell is scorable when the noise-free
image has a 3x3x3 local maximum above 168 on it. Additive 16-step regime,
duplicate seeds per 100 cells / cells lost per 100:
- Window 11x11x1 (current): 108 / 5.5. One extra seed per cell, from adjacent
  planes; about 100 times the 2D tie duplicates.
- 11x11x3: 1.6 / 17.5; 11x11x5: 1.2 / 28.1. The 11-pixel in-plane window,
  tuned on 2D crops, suppresses dim cells in neighbouring planes.
- 5x5x1 (ClearMap's default in-plane size): 123 / 0.7; 5x5x3: 2.0 / 2.7.
- Dip 10% on 5x5x1: 0.5 / 2.0 (0.2-0.8 / 1.8-2.2 across all three regimes).
  Fixed h_max (h=17) on 5x5x1: 0.1 / 2.6, but 1.9 / 2.2 under texture.
- dog_filter (7,7,3) with 11x11x3: 0 / 16.6; it does not offset the window loss.
- dog_filter (5,5,3) with 5x5x3: 0.0 / 1.5 (texture 0.0 / 1.6, continuous
  0.0 / 1.0), the best of every method in all three regimes. Kernel (7,7,3)
  with 5x5x3 gives 0.0 / 2.8, no better than no filter. With a per-plane 5x5x1
  window, either kernel still gives about one extra seed per cell. Run with
  --methods dog_w5 baseline_w5; the baselines reproduce the full run exactly.
In 3D, the window choice matters far more than any merge rule. dog_filter
(5,5,3) with a 5x5x3 window needs no new code, only existing ClearMap settings.
Losses depend on cell density, so check the window and kernel on real 3D data
before choosing.

Threshold on the DoG output, 2026-11-02 (dog_thr methods; maxima and threshold
both on the DoG image, as Cells.detect_cells_block does with dog_filter on):
- DoG gain, the response at an isolated cell's centre per unit peak intensity:
  kernel (5,5,3) 0.082 / 0.077 / 0.064 for cell sigma 2.8 / 3.8 / 4.8 um;
  (7,7,1) in 2D 0.078 / 0.077 / 0.065. 168 x mid gain = 12.9 for both.
- 3D, (5,5,3) kernel, 5x5x3 window, lost cells per 100 (no duplicates):
  0.5x and 0.75x (9.7): 0.6-1.0; 1.0x (12.9): 2.1-2.7; 1.25x: 8.9-9.7;
  1.5x: 17.6-18.3. At 1.0x, dim cells of the largest size fall below the
  threshold (200 x 0.064 = 12.8), so match the threshold to the largest
  expected cell (168 x 0.064 = 10.8) or set it lower.
- 2D, (7,7,1) kernel, 11x11x1 window: 0.27-0.40 lost at 0.5-0.75x and
  0.36-0.90 at 1.0x; 4-11 at 1.25-1.5x.
- No false seeds at any threshold, but the scenes contain no objects fainter
  than 200 and no autofluorescence, so a low threshold is never penalised.
  The benchmark sets only an upper bound; choose the lower bound on real data,
  starting near 10 and checking false detections.

Shape-detection threshold on the DoG output, 2026-11-02 (--shapes; 3D, 40
scenes per regime, ~5,600 cells each). Seeds from dog_filter (5,5,3) with a
5x5x3 window at DoG threshold 9.7; seeded watershed on the DoG output restricted
to DoG > shape threshold, against the no-DoG pipeline (watershed on the image,
mask > 168). Each found cell's region is compared with its half-maximum
footprint, a brightness-independent true extent. Additive 16-step regime; the
other two regimes agree within about one point:
- No DoG: 16.6% of dim cells (<400) under 5 voxels; size / true size 0.64 dim,
  4.58 bright (bright cells 7.2 times larger relative to their extent).
- DoG shape threshold 3.2 / 6.4: no small cells; size ratio dim 2.33 / 1.37,
  bright 4.41 / 3.58.
- DoG shape threshold 9.7, equal to the seed threshold: 1.5% of dim cells under
  5 voxels; ratio 0.83 dim, 3.00 bright; median IoU 0.72 dim, 0.33 bright.
- DoG shape threshold 12.9, above the seed threshold: 5.0% of dim cells get no
  region (their seed lies outside the mask) and 29.2% fall under 5 voxels.
Set the shape threshold equal to, never above, the seed threshold. Measured size
grows with brightness in every setting, so a size filter partly filters by
brightness.

Per-cell relative shape threshold, 2026-11-02 (--shapes --methods rel; same
scenes). Watershed on the DoG with a loose mask (DoG > 3.2), then each region is
cut to the voxels at or above a fraction of the DoG value at its own seed, keeping
the part connected to the seed (relative_cut). Size / true size dim / mid /
bright, additive 16-step (other regimes within 0.03):
- 50% of own DoG peak: 0.87 / 0.91 / 0.92; IoU 0.80 / 0.80 / 0.81; no cell
  under 5 voxels. Bright cells are 1.06 times dim ones, against 3.6 times for
  the absolute DoG threshold 9.7 (IoU there 0.72 dim, 0.33 bright).
- 25%: 1.79 / 1.90 / 1.97, IoU 0.51-0.56. 75%: 0.34-0.36, and 15-20% of cells
  in every band fall under 5 voxels.
- 50% of own image peak: 1.21 / 1.24 / 1.21, IoU 0.77-0.82. Partly circular,
  because the reference footprint is defined at half of each intensity peak.
A 50% relative cut on the DoG makes measured size independent of brightness, so
a size filter would filter by size alone. ClearMap has no such option; it would
need about ten lines in shape detection. Caveat: the synthetic cells are
Gaussian, for which a fraction of the peak is a fixed fraction of the radius
at every brightness. Flat-topped or irregular real nuclei may behave
differently; check on real 3D data.

Flat-topped cells, 2026-11-02 (--shapes --profile flat; same random draws).
Each cell is a uniform sphere, radius equal to the Gaussian's half width at half
maximum (3.3-5.7 um), rendered with sub-voxel partial volume and blurred by a
Gaussian point-spread function (sigma 1/1/2 um). --truth sphere scores against
the unblurred sphere (voxels at least half inside), independent of any
threshold. Size / true size dim / mid / bright, IoU dim / bright, additive
16-step, sphere truth:
- Absolute DoG 9.7: 0.91 / 1.54 / 2.15, IoU 0.78 / 0.46.
- Relative 50% of own DoG peak: 0.64-0.67 in every band, IoU 0.63-0.65.
  Still brightness-independent, but too tight; 25% gives 1.20-1.25 (IoU
  0.79-0.80) and 75% leaves about 62% of cells under 5 voxels. The right DoG
  fraction depends on the cell profile: 50% for Gaussian cells, nearer 25-35%
  for flat ones.
- Relative 50% of own image peak: 1.00 in every band, IoU 0.89-0.93 (texture
  regime 0.94-0.96, IoU 0.84-0.86). For a blurred uniform object the edge sits
  at half the interior intensity, so this cut finds the edge at any brightness.
  For Gaussian cells it gave 1.15-1.24. It needs the background-corrected image
  as well as the DoG.
- Without a DoG, flat tops in 16-step data give 1.5-8.5 duplicate seeds per
  100 cells even with a 5x5x3 window; with the DoG, none.
- DoG seeds lose 2.1% of dim flat cells, against 1.1% of dim Gaussian cells.
The relative cut removes the brightness bias for both profiles. If one cut is
used, cut on the background-corrected image at 50% of each cell's own value;
a DoG-based fraction must be calibrated on real nuclei.

Irregular nuclei, 2026-11-02 (--shapes --profile irregular --truth sphere).
Each flat-topped sphere becomes a randomly oriented ellipsoid of the same volume
(axes vary by about 15%), with a lumpy outline (radius varies by about 12% with
direction) and chromatin texture (intensity varies by about 25% at 1.5 um), then
is blurred. Interior intensity averages about 0.6-0.8 of the cell's peak. The
reference is the unblurred deformed shape. Extra randomness comes from a spawned
generator, so the main draws match the other profiles. Additive 16-step:
- Relative 50% of own image peak: 0.91 / 0.92 / 0.93, IoU 0.77-0.80 (texture
  regime 0.89-0.90, IoU 0.75). Still brightness-independent; texture makes it
  slightly small, because a textured cell's peak sits on a bright spot.
- Relative 25% of own DoG peak: 1.23-1.32, IoU 0.71-0.72. 50%: 0.64-0.68,
  IoU 0.61-0.65. 75%: 57-59% of cells under 5 voxels.
- Absolute DoG 9.7: 0.83 / 1.50 / 2.12, IoU 0.70 / 0.47.
- No DoG: 3.5-8.8 duplicate seeds per 100 cells and 14.7% of dim cells under
  5 voxels; with the DoG, almost no duplicates (0.05 per 100).
Across Gaussian, flat and irregular cells, the 50% image cut stays within 0.9-1.24
of true size and is brightness-independent; every absolute threshold makes
bright cells about 2-4 times larger, relative to their true extent, than dim
ones.

Smoothed reference for the 50% image cut, 2026-11-02 (rel_img_smooth; --methods
rel_img on all three profiles, same scenes). The cut stays on the unsmoothed
image; only each cell's reference value is read from the image smoothed by a
Gaussian of 1 or 2 um. Size / true size dim-bright (IoU), additive 16-step:
- Seed voxel (rel_img): Gaussian 1.21-1.24 (0.77-0.82), flat 1.00
  (0.89-0.93), irregular 0.91-0.93 (0.77-0.80).
- Smoothed 1 um: Gaussian 1.26-1.33 (0.75-0.76), flat 1.00 (0.89-0.93),
  irregular 0.94-1.00 (0.78-0.81). Under strong texture: flat 0.94-0.96 -> 1.00,
  irregular 0.89-0.90 -> 0.92-1.00. No cell under 5 voxels in any profile.
- Smoothed 2 um: too low a reference; Gaussian 1.73-1.92, flat 1.22-1.28,
  irregular 1.20-1.29.
A 1 um smoothed reference removes the texture undersizing on nucleus-like cells
at a small cost on Gaussian ones (about 0.05-0.1 larger). For nuclei, use 50% of
each cell's value in the image smoothed by about 1 um, i.e. about half the
point-spread width.

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

### Relative cut implemented in ClearMap shape detection, 2026-11-02

ClearMap/Analysis/Measurements/shape_detection.py: detect_shape gains
relative_cut, relative_cut_sigma and reference; new cut_relative trims object
i + 1 to the pixels at or above relative_cut x the reference image's value at
seed i (read from the reference smoothed by relative_cut_sigma pixels), keeps
the part connected to the seed, and removes labels without a seed. Fractional
seeds (h_max centres) are rounded. Cells.py: shape_detection defaults
relative_cut=None and relative_cut_sigma=None (results unchanged), parameter
docs added, and detect_cells_block passes the image before the DoG filter
(after background correction and equalization) as the reference.

Suggested settings from the synthetic benchmarks, to confirm on real data:
relative_cut=0.5, relative_cut_sigma of about 1 um in pixels (0.5, 0.5, 0.2 at
2 x 2 x 5 um voxels), and a low shape threshold (about a quarter of the maxima
threshold) so the watershed does not cut cells short before the relative cut.
The GUI config does not expose the new parameters.

Checks: tests/analysis/test_shape_detection.py, 9 tests, pass with the real
compiled voxelizer (graph IO module stubbed locally because graph_tool is not
installed here). Full detect_cells on two Gaussian blobs of 10x different
brightness: absolute threshold 150 gives 189 and 1,654 voxels; relative_cut 0.5
gives 205 and 205. On flat-topped balls, master's tied-plateau seeds (defect 1)
still give dozens of seeds per ball; the relative cut does not fix that.

### Upstream tied-plateau fix ported, 2026-11-02

Cherry-picked upstream 33365efe (label_representatives in maxima_detection.py)
and 7f681ddf (detect_cells_block labels the maxima mask with full 3x3x3
connectivity and keeps one pixel per connected group when h_max is None), both
by Gael Cousin, 2024-08-08; authorship kept, cherry-pick IDs recorded. A
trivial end-of-file conflict in maxima_detection.py was resolved by appending
the upstream function unchanged. A separate commit replaces the annotation
tuple[np.ndarray, ...] with typing.Tuple: on Python 3.8 the upstream line makes
importing maxima_detection fail ("'type' object is not subscriptable"), and
master's environments pin Python 3.7. Verified on Python 3.8.20 before and
after.

Check: full detect_cells on two flat-topped balls (radius 6, blur 0.7, 10x
apart in brightness) went from dozens of seeds per ball to one each. With
relative_cut 0.5 both measure 919 voxels, their exact half-maximum volume;
the absolute threshold gives 919 and 1,527. tests/analysis/test_maxima_detection.py
adds 3 tests (also passing on Python 3.8).

Side effect, as upstream: the kept pixel is the group's first in array order,
not its centre, so a cell with a wide flat top is reported off-centre (2 voxels
for these balls). Not ported: v3.1.x's later masking of maxima by the shape
threshold and its other changes. Defects 2 and 3 (summed marker IDs, write
race) remain on this branch.

### Upstream direct-marker fix ported, 2026-11-03

Ported upstream 2fcaad7e and 7a849f6d (Gael Cousin, 2024-09-09) as one commit
with his authorship: 2fcaad7e alone leaves detect_shape with an unfinished line
("peaks = "). detect_shape now writes each seed's label at its own pixel with
labeled_pixels_from_centers instead of voxelizing radius-1 spheres weighted by
seed ID. This fixes defects 2 and 3: summed IDs (adjacent seeds 1 and 2 used to
give both seed pixels a false label 3) and the parallel write race, since the
voxelizer is no longer used for markers.

Follow-up commit: labeled_pixels_from_centers raised IndexError on fractional
seeds (h_max centres of mass), which the old voxelizer truncated with a C cast.
New seed_pixels truncates the same way and is used for both the markers and
the relative cut (cut_relative rounded before, which could read a different
pixel than the marker). Indexing with tuple(centers.T) replaces upstream's
3D-only unpacking and works in any dimension on Python 3.7.

Checks: 16 tests pass (4 new). Pipeline runs on Gaussian blobs and
flat-topped balls give exactly the same results as before the port.

Found while testing: master's h_max path still fails before shape detection,
because detect_cells_block passes the block, not its array, to
find_center_of_maxima (upstream issue #46, fixed in 7fbc49ee on
v3.1.x-experimental, not ported). With that one-line fix applied in memory,
h_max runs through shape detection, but finds one of two blobs:
find_center_of_maxima still drops the last maximum (also fixed only on
v3.1.x-experimental).

### Upstream h_max fixes ported, 2026-11-03

Ported four upstream commits by Charly Rousseau (2026-10-22, v3.1.x-experimental),
authorship and cherry-pick IDs kept:
- b3728b2a: grey reconstruction calls scikit-image's reconstruction directly.
  master imported a private module removed in scikit-image 0.20, and its
  environments do not pin scikit-image, so h_max failed on any recent install.
  Applied by hand: master still has the file as GreyReconstruction.py, in an
  older form.
- 914aa527: find_center_of_maxima gives every maximum its centre (it passed
  np.arange(1, n_label) and dropped the last).
- d0b75e0a: h_max_transform works in float for integer images, so uint16
  source - h_max no longer wraps around and raises.
- 7fbc49ee (#46): detect_cells_block passes the block's array, not the block,
  to find_center_of_maxima, so the h_max path no longer crashes.
Test conflicts were resolved by keeping both sides.

Follow-up commit: reconstruct passes footprint= on scikit-image 0.19 and later and
selem= before (upstream's call fails on 0.18.3; verified on 0.18.3 and 0.26.0),
and upstream's h_max cell-detection test reads master's tuple result.

Checks: 25 tests pass across test_maxima_detection.py, test_shape_detection.py
and test_cell_detection_with_h_max.py. A full detect_cells with h_max on a
uint16 image with zero background now finds both blobs (189 and 1,654 voxels);
before these ports it crashed. compare_dip_vs_hmax.py's report of the shipped
h_max centres now reflects the fixed code.

Still open, on master and upstream alike: face-only labelling in
find_center_of_maxima splits flattened plateaus that touch diagonally, and the
11x11 window rejects a lowered peak next to a brighter neighbour's unchanged
slope.
