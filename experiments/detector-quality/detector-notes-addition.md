
## 6. Confirmed local detector issues (2026-10-26)

These findings concern controlled NEATmap demo crops and synthetic inputs in the
local installed ClearMap runtime. They are not validation of the lab datasets or
biological cell counts. No production detector or original checkout was modified.

- **Duplicate plateau seeds:** with `h_max=None`, the maximum filter marks every
  tied maximum pixel and the detector enumerates each as a seed. Connected flat
  maxima can therefore produce multiple detections for one candidate object.
  A separate experimental connected-plateau correction reduced accepted centers
  from 27 to 25 and 20 to 18 in two crops under fixed single-thread execution.
  It does not merge disconnected peaks; a human-reviewed single object still
  has two centers. See `iDisco-analysis/peak-plateau-review.md`.
- **Invalid watershed marker IDs:** shape detection voxelizes seed IDs as weights
  using overlapping radius-one neighborhoods. Adding overlapping IDs produces
  invalid categorical markers: synthetic seeds 1 and 2 produce a spurious label
  3, including with one thread.
- **Concurrent marker-write race:** the weighted voxelizer uses parallel seed
  iteration and unsynchronized additions to shared pixels. Fixed demo seeds
  produced differing marker and watershed arrays across repeated multithreaded
  runs; seed enumeration stayed identical and frozen markers gave repeatable
  watershed results. The isolated trace did not reproduce the earlier changing
  accepted totals, so not every earlier count variation has been attributed.
- **One process does not guarantee one native thread:** the cell detector derives
  native threads from CPU count and process count. Controlled tests explicitly
  force one native thread. This improves repeatability but does not correct
  invalid summed marker IDs.

Evidence: `iDisco-analysis/thread-trace-review.md` and
`iDisco-analysis/test-data/thread-trace-20261026T025802411050Z/report.json`.
The next controlled experiment compares direct categorical seed markers with
the original serial marker construction while keeping plateau handling unchanged.
Changes to shape sizes and size-filter acceptance require review before adoption.
