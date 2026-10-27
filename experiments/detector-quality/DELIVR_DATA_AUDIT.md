# DELiVR data audit — 2026-10-27

## Agreed milestone order
1. Audit DELiVR reference data, then measure unchanged ClearMap baseline accuracy once the data gate passes.
2. Compare experimental corrections against that baseline on held-out examples.
3. Human review of evidence before adopting corrections.
4. Package execution, independent subscription-agent QC, human checkpoints, reports and resume behavior.
5. Run the frozen test on the server and verify matching results.

Current status: step 1, data audit incomplete; ClearMap has not run on these patches.

## Download and provenance
Pinned official erturklab/delivr_cfos commit: `51ef796da883ace0afbbf589630b0e756dd3c6d3`.
Downloaded raw/gt pairs `patchvolume_1008_0.nii.gz` and
`patchvolume_1147_0.nii.gz` (about 4.4 MB total), chosen by filename before image inspection.
All four files match Git blob hashes and sizes; SHA256s recorded in
`test-data/delivr-audit/audit.json`. Inventory saved in source-tree.json.
NIfTI reader nibabel 5.2.1 installed without dependencies into the ignored audit
folder only; existing ClearMap environment unchanged.

## Findings
- Both pairs have matching 100x100x100 shapes and matching raw/mask affine matrices.
- Both headers report spacing 1,1,1 with UNKNOWN physical units, qform=0,
  sform=2 and diagonal affine -1,-1,1. These do not verify physical calibration.
  The paper describes acquisition XYZ 1.625,1.625,6 micrometres, but the exported
  patch spacing/resampling and microscope-axis mapping are not established.
  Anatomical orientation codes from these generic affines are not treated as verified anatomy.
- Both ground-truth files have values exactly {0,1}: binary semantic masks,
  not individual-cell IDs. Positive connected components depend on connectivity:
  427/416/411 for patch1008 and 145/140/140 for patch1147 (6/18/26 neighbors).
  These are component counts, NOT established cell counts. Splits, touching cells,
  and annotation fragments require an instance-reference policy or original instance labels.
- Continuity was measured along every array axis, without assuming a Z mapping.
  No identical adjacent planes. Axis2 has worst adjacent correlation -0.062 at
  10/11 for patch1008 and 0.554 at 28/29 for patch1147. Patch1008 has a visually
  abrupt spatial-pattern transition at 10/11; cause unknown. Patch1147's displayed
  transition retains broad structure but changes local object appearance.
  See continuity-qc.png. Statistical/visual checks do not prove acquisition continuity.
- Official current inventory contains 48 raw images and 41 masks, with seven
  missing partners listed in audit.json. This does not recover the paper's 39/9 split.
- The inspected training repository supplies a configurable test_list (default
  /data/test) or generates a random split; no published patch identity manifest
  was located in the inspected trees/config/code. Do not infer test identity from
  missing masks, directory names or a newly generated random split.

## Evaluation protection and next prerequisite
Both downloaded pairs are QA-only, with split assignment UNRESOLVED. No threshold
tuning, training, detector evaluation, or relabeling has been performed. Preserve
the paper's test set by withholding all dataset use until its identities can be
established; do not describe an invented split as the published split.
Need authoritative patch calibration/export provenance, published test identities,
and individual-cell reference semantics before claiming baseline counting accuracy.
If unavailable in archived resources, prepare a clarification request for the authors
for the user to send; do not contact them without authorization.

Sources:
- https://pmc.ncbi.nlm.nih.gov/articles/PMC11239522/
- https://github.com/erturklab/delivr_cfos/tree/51ef796da883ace0afbbf589630b0e756dd3c6d3/training_data/cFos
- https://github.com/erturklab/delivr_train

Reproduce with WSL clearmap Python and PYTHONPATH set to
`test-data/delivr-audit/python-deps`, running `audit_delivr_subset.py`.

## Archived-release follow-up
- Zenodo concept10908720 resolves to record10908721, archive delivr_cfos-v1.0.0.zip (445606862 bytes). Git tag v1.0.0 is b12b003a0ac32a23314486fa6e20d35173baf579. Inspected its Git tree instead of downloading the large archive. All89 cFos raw/gt blobs match the current inventory exactly:48 raw plus41gt.
- Training archive10909998 identifies delivr_train-v1.0.1. Its tree has code/config/weights but no named test-split manifest or additional annotation files.
- Archived cell_analysis.py explicitly binarizes masks and derives connected components (documented26-connectivity). Thus binary references are intentional in the public evaluation implementation; distinct biological cell IDs are not recovered by that procedure.
- Code inspection also shows get_patch_overlap does not enforce one-to-one matching: multiple predicted components overlapping one target each contribute TP. A prediction overlapping several targets is FP but adds those targets to hit_target, reducing FN. This implementation should not silently become our biological-count metric; any reproduction must be reported separately from one-to-one detection scoring.
- Supplementary handbook retrieval was attempted through PMC and publisher CDN; PMC returned a browser challenge and CDN failed through web, Windows and WSL TLS. Handbook content remains uninspected; no claim that it lacks answers.
- Remaining external facts: exact published split, calibrated patch axes/spacing, discontinuity/export provenance, original instance references. Prepared DELIVR_AUTHOR_QUESTIONS.md for user review; nothing sent. Data remains QA-only and ClearMap has not run.
