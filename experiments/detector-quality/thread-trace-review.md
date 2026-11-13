# Detector thread trace — 2026-10-26

Diagnostic: trace_detector_threads.py. Completed report:
test-data/thread-trace-20261026T025802411050Z/report.json.
Local WSL only; no ClearMap source or installed package was edited.

## Isolated failure

shape_detection.detect_shape constructs watershed markers with
Voxelization.voxelize using its default sphere radius (1,1,1), assigning seed
IDs as weights. DevolvePointListCode.pyx devolve_weights loops over seeds in
OpenMP prange and performs shared sink[j] += weights[n] without synchronization.
Nearby seed neighborhoods overlap, so concurrent writes race. Separately,
adding IDs is not a valid rule for resolving overlapping categorical labels.

## Controlled evidence

Two frozen 256x256x1 demo crops, fixed threshold 168, fixed 11x11x1 peak mask,
identical ordered seed coordinates, twelve repetitions at each of 1,4,8 threads:

- Seed enumeration was identical to numpy.argwhere in every repetition.
- Center marker arrays: 1,3,3 unique outputs at 1,4,8 threads respectively.
- Right marker arrays: 1,3,9 unique outputs; watershed arrays: 1,3,8.
- Watershed with frozen serial markers was identical across all repetitions.
- Accepted totals stayed 27 (center) and 20 (right) in this isolated test.
  Thus this test reproduces label/shape variability, not the earlier 27/26/25
  full-pipeline count sequence. Further stage instrumentation would be needed
  to attribute every earlier count change exclusively to this race.

Minimal two-seed test (IDs 1 and 2, adjacent pixels), thirty repetitions:
radius-one markers include a spurious label 3 even with one thread; four threads
produced two distinct arrays. Eight threads happened to produce one array in
this small sample, which does not disprove the race. Radius-zero control produced
only labels 0,1,2 and identical arrays at every tested thread count.

## Implication

Single-thread execution remains an interim repeatability measure, not a
correctness fix. A targeted future correction should construct categorical
markers directly at unique seed coordinates, reject/resolve duplicate seed
coordinates explicitly, and define deterministic conflict handling if expanded
markers are required. An atomic addition would not fix invalid summed IDs.

The zero-radius diagnostic is not yet a validated replacement detector. Test
its shape and size-filter effects against human-reviewed single cells and
touching cells before promotion. Plateau duplicate detection is a separate
issue and should remain a separate comparison.

The first diagnostic attempt failed in the installed voxelizer's pixel mode;
the successful run used sphere radius zero as the non-overlapping control.
