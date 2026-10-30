# Direct categorical marker experiment — 2026-10-26

Completed output: `test-data/direct-markers-20261026T030829096851Z/`.
Script: `test_direct_markers.py`. Local demo only; original source unchanged.

Fixed frame 5, channel 0, center/right 256-pixel crops, background 21x21,
maxima 11x11x1, threshold 168, accepted size 5–500 pixels, one native thread.
Plateau correction disabled. Direct markers assign one integer ID at each
unique seed coordinate; duplicate, fractional and out-of-bounds coordinates
are rejected. Seven synthetic checks passed.

Three full-pipeline repeats per variant and crop produced identical output
tables. Input seed arrays were identical between variants (98 center, 55 right).

| Crop | Baseline accepted | Direct accepted | Changed sizes |
|---|---:|---:|---:|
| Center | 27 | 25 | 18 |
| Right | 20 | 21 | 27 |

Acceptance changes, in crop coordinates:
- Center (15,190): size 5 to 3, no longer accepted.
- Center (136,142): size 5 to 2, no longer accepted.
- Right (190,170): size 4 to 5, newly accepted.

These are threshold-edge changes, not evidence of improved biological accuracy.
The comparison image was inspected; multiple centers remain on the previously
reviewed upper bright right-crop object. Marker correction alone is not a
duplicate-peak correction. Keep both interventions separate for review.

The original pipeline discards zero-size seed rows before returning results:
baseline returned 89/50 rows; direct returned 98/55. Thus output row counts
cannot be used to assert unchanged seed generation. This experiment checks
the actual seed arrays and compares output tables by coordinates, treating
missing rows as zero-size for the size-change audit.

Two earlier folders are incomplete attempts: diagnostic collection initially
assumed shared worker memory, and the next attempt incorrectly assumed returned
row arrays were the complete seed arrays. Neither contains a completed report.

Next human checkpoint: inspect the three objects whose acceptance changed with
raw and segmented close-ups before combining this change with plateau handling.
No production adoption, SSH run, model training, or biological count validation.

## Close-up investigation

Verified reconstruction and figure:
`test-data/marker-closeups-20261026T031638508434Z/three-objects.png`.
Script: `inspect_changed_markers.py`; full direct segmentation matched saved
output exactly, and all three baseline/direct sizes matched saved CSV rows.

- A, label 5: the local footprint is three pixels in both methods. Original
  markers add two distant pixels at (4,118) and (4,119), where seed IDs 2 and 3
  sum to 5. This wrongly raises its measured size to five.
- B, label 57: the local footprint is two pixels in both methods. Overlapping
  seed IDs 28 and 29 create marker 57 at (87,35), which acquires three distant
  pixels at (86–88,35). These falsely raise B's measured size to five.
- C, label 44: overlapping seeds 44 and 45 create marker 89 at C's own seed
  coordinate (190,170). Direct markers restore that pixel to label 44, changing
  its size from four to five. Other nearby seeds remain; this is not a complete
  object segmentation or a plateau correction.

Thus A/B did not shrink locally: their original sizes were contaminated by
remote label collisions. C lost its own seed pixel under the original markers.
Visual interpretation remains provisional: A is a small weak spot, B is poorly
defined against its background, and C is a clearer elongated bright object.
These images establish the computational defect, not biological cell identity.
