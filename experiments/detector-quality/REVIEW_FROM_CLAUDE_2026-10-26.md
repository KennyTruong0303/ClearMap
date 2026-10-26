<!-- Code review written by Claude (Claude Code) for Codex. Read-only review; nothing in this repo was changed by Claude except adding this file. Source copy: C:\dev\CLEARMAP_REVIEW_2026-10-26.md -->

# Review: ClearMap detector-quality work, codex/work @ fa101e9c

Reviewed 2026-10-26 by Claude (read-only, nothing changed in ClearMap-work). Scope: the
`experiments/detector-quality/` commit, checked against the ClearMap 2.1.4 source in the same
checkout.

## Overall

Strong, careful work:
- Human labels, uncertain labels (A/B) and provisional anchors are kept apart.
- Tuning data and fresh data are kept apart.
- Stage-level results are never presented as accuracy.
- Repeatability checks are run.
- Hashes are recorded for the migration.
- The 6% rule is correctly **not** promoted.

No production code has changed yet. That's correct at this stage.

## 1. The three "confirmed defects" are real in the source

| Claim | Where in ClearMap | Verdict |
|---|---|---|
| Tied plateaus → multiple seeds when `h_max=None` | `ImageProcessing/Experts/Cells.py:394`: `centers = ap.where(maxima)` marks every voxel of an equal-valued plateau as a seed. Only the `h_max` branch (`find_center_of_maxima`) collapses connected maxima. | Confirmed |
| Overlapping weighted markers add seed IDs | `Analysis/Measurements/shape_detection.py:75`: `vox.voxelize(seeds, weights=np.arange(1, N+1))`, default `method='sphere', radius=(1,1,1)`, so seeds within 2 voxels overlap. `ParallelProcessing/DataProcessing/DevolvePointListCode.pyx:148`: `sink[j] += weights[n]` sums the IDs, and the sum can equal another seed's ID elsewhere. | Confirmed |
| Parallel marker writes race | Same loop: `for n in prange(n_points)` with a non-atomic `sink[j] += ...`. Concurrent writes to one voxel can be lost. | Confirmed |

These are worth reporting upstream (ClearAnatomics/ClearMap) independently of the 6% rule.

## 2. Notes for porting `markers()` (direct markers) into ClearMap

- **Float seeds in the `h_max` path:** `markers()` rejects non-integer seeds. `ap.where`
  returns integers, but with `h_max` set, `find_center_of_maxima` returns centres of mass, which
  can be fractional. Ported as-is, it would raise for every `h_max` run. Decide on a rounding
  rule (round, plus a collision check after rounding) and test both paths.
- **Shapes can change even with no overlap:** the original sphere markers pre-assign each
  seed's 3×3×3 neighbourhood before flooding. Direct markers start from one voxel and let
  intensity decide. The saved comparison already shows identical shapes for these crops, but on
  real 3D data, measure size and intensity changes for non-overlapping seeds separately from
  the overlap fix. Otherwise two effects get mixed together.
- **Duplicate check:** the duplicate-coordinate guard can't trigger on the `ap.where` path but
  can after rounding. Keep it, and make it an explicit, logged decision rather than a crash.

## 3. The "unexplained" extra −2 accepted detections is explained by the size filter

From the log: 5 merges remove accepted seeds, so −5 was expected, but −7 was observed. The size
changes the log lists account for exactly the difference, against the accepted range 5–500 px:

| Seed | Size | Acceptance |
|---|---|---|
| x1400_y200 (246,44) | 10 → 3 | accepted → rejected (−1) |
| x1400_y200 (246,46) | 6 → 1 | accepted → rejected (−1) |
| x1400_y200 (247,45) | 3 → 13 | rejected → accepted (+1) |
| x1400_y450 (194,5) | 5 → 4 | accepted → rejected (−1) |
| **Net** | | **−2**, so total −7 |

So the count arithmetic is closed. What's still open is *why* those sizes change.

**Hypothesis to test: watershed tie-breaking.** skimage's watershed orders its priority queue by
(value, age), with age assigned globally as pixels are pushed. Removing any marker shifts the age
of everything pushed after it, so pixels on **equal-intensity ties** can switch basins anywhere in
the image, not just near the merge. The three x1400_y200 seeds sit within about 2 px of each other
and trade area among themselves (10+6+3 → 3+1+13). That's the signature of neighbours competing
over tied or near-flat pixels. Keeping the original marker IDs (the `fixed-id-trace` check)
wouldn't prevent this, because queue age isn't the label ID.

Suggested checks:
1. For every pixel that changed label, test whether its intensity is tied with the boundary it
   moved across. If all changed pixels are ties, this is tie-breaking, not a bug in the merge rule.
2. Rerun with a deterministic tie-break that doesn't depend on queue order. For example, add a
   tiny distance-to-seed term to the flooding image, or use `compactness`. Check whether the
   distant changes disappear.
3. If confirmed, the production design should make the result independent of which unrelated
   seeds exist. Otherwise per-cell sizes aren't stable under small seed edits.

## 4. Housekeeping

- **Large stray file:** `ClearMap-work/Dataset226_.../` is an untracked 1.1 GB copy of the
  RESPAN model, unrelated to ClearMap. A `git add -A` would try to commit it. Delete it, or add it
  to `.gitignore`.
- **Evidence isn't in git:** `experiments/detector-quality/test-data` (166 MB) is ignored by git,
  which is reasonable, but nothing backs it up. It's covered only if `D:\git-backups` or another
  backup includes it.
- **Interpreter path:** the README runs the scripts with
  `/home/kenny/miniconda3/envs/clearmap/bin/python`. The laptop's WSL install is described
  elsewhere as `~/software/ClearMap` with env `clearmap`, and the lab server uses micromamba at
  `~/.local/envs/clearmap`. Worth stating the interpreter per machine once remote runs start.
- **Monkeypatching:** the experiments monkeypatch `sd.detect_shape` and
  `Cells.detect_cells_block` in-process. That's fine for experiments, but the eventual ClearMap
  change should be a real parameter, for example `marker_mode='direct'|'sphere'`, with the old
  behaviour still available for comparison.

---

# Review 2: codex/work @ 133e2505, "Document component segmentation validation and watershed findings"

Reviewed 2026-10-26 (read-only). Files: `validate_component_segmentation.py`,
`check_component_pipeline.py`, `trace_watershed_locality.py`, plus the log additions.

## Verdict

Good follow-up:
- The tie-breaking hypothesis from review 1 is now properly confirmed. There's a minimal
  two-island reproducer, and the unique-priority diagnostic removes the unrelated changes.
- The per-component watershed is the right shape of fix.
- The checks are strong: 27 synthetic cases, invariants, padding and memory-layout tests, an
  "unrelated components unchanged after deleting a seed" test, and an end-to-end
  `detect_cells` run matching the stage output.
- The conclusions stay modest. Codex keeps "stable" separate from "accurate" and doesn't adopt
  anything into production.

## Findings

1. **The timing claim is mislabelled.** The log says 1.3–10.6 ms "per component" against
   0.7–1.2 ms globally. The code times a single call over the **whole 256×256 crop**. From the
   report: 0.28–10.63 ms per crop for components against 0.45–1.22 ms for global, so 6.7–14.5×
   slower on crops with seeds. Please correct the wording. "Per component" understates the cost
   by roughly 50–90×, which matters when extrapolating to a whole brain.

2. **Easy speed-up: most components don't need a watershed at all.** In the image-26 crops, about
   88% of seeded components hold **exactly one seed** (crop x800_y200: 69 of 78; another crop:
   47 of 52). A connected component with one seed is flooded entirely by that seed, so the
   result equals assigning that seed's ID to the whole component. Running watershed only on
   components with two or more seeds gives identical output, removes most of the Python-loop
   and watershed calls, and should close most of the slowdown. Add a test that compares the
   shortcut with the current `segment()` on the 27 synthetic cases and the 8 crops.

3. **Ties inside multi-seed components are still arbitrary.** Per-component isolation makes
   results independent of *unrelated* seeds. But where two seeds in the *same* component meet
   on an equal-intensity plateau, the winner still depends on watershed queue order (pixel
   raster order). The log already says the new sizes (10/1/3/4) aren't more accurate than the
   old ones (10/6/3/5); that's correct, and they remain order-dependent. Codex rightly rejected
   unique-index perturbation as arbitrary. A *principled* tie-break is a different thing and is
   worth one experiment: on exact ties, assign the pixel to the **geodesically nearest seed**
   inside the mask. For example, run the watershed on the intensity first, then reassign only
   pixels whose intensity is tied across a boundary by geodesic distance. Or compare
   skimage's `compactness` > 0 restricted to plateaus. The test is whether boundary positions
   become invariant to array transposition and flipping. The current version would fail that
   test on ties.

4. **Use one implementation (minor, not a bug).** `trace_watershed_locality.component_watershed`
   passes unmasked `markers[sl]`, while the validated `segment()` masks them with
   `np.where(local, ...)`. I checked that scikit-image drops markers outside the mask (0.20 in
   your WSL ClearMap env, and 0.24), so the diagnostic results stand. Still, reuse `segment()`
   so there's one implementation to validate.

5. **Scope to carry forward:**
   - Every full-detector check ran a single block (`overlap=0`, one Z block, one thread).
   - Real ClearMap runs process overlapping blocks, so components cut by block edges will be
     segmented per block.
   - Before adoption, test that a cell straddling a block boundary gets the same size and
     label as in a single-block run, using the configured overlap.

## Suggested next steps (in order)

1. Fix the timing wording.
2. Add the one-seed shortcut with an equivalence test.
3. Try the geodesic tie-break on the multi-seed components and test it under transpose/flip.
4. Test block boundaries.
5. Only then review the three acceptance changes and revisit the 6% merge rule.
