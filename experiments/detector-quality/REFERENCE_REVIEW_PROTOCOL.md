# Manual 3D reference pilot

Open test-data/reference-review-v1/review.html directly in a browser (self-contained),
or use the local preview at http://localhost:8765/review.html while its server runs.

Six disjoint predefined 64x64x30 windows from the verified public cellfinder sample
are available. Automatic detections are hidden. The manifest fixes the source hash,
window origins, voxel sizes, display ranges and prospective split: R1/R3/R5 tuning,
R2/R4/R6 held out. These are windows from one sample, not independent brains. They
are newly selected for this annotation pilot, not guaranteed unseen during earlier
whole-sample inspection. Do not tune against held-out labels after annotation.

Review a distinct fluorescent object through Z and mark its center once, on its
best-centered plane. Mark doubtful identity or separation as uncertain. Use the
edge label for objects cut by XY crop boundaries or the first/last Z plane. Artifact
marks are optional specific examples; absence of a mark is not a validated negative
unless the entire region has been reviewed. Record disagreements rather than force
an answer. Stain and biological identity are not confirmed for this sample.

The four statuses are object, uncertain, artifact, edge. No labels have been supplied
by the agent. The UI smoke-test annotation was removed. A second knowledgeable
reviewer should annotate independently before seeing the first review; adjudicated
labels can then become a reference. Agent review is supporting evidence, not ground
truth. No accuracy target or matching distance has been silently selected.

Download labels JSON before closing; there is no automatic disk save. The page can
resume from its exported JSON and rejects wrong source/review IDs. Retain reviewer
identity, completion flags and notes. Do not replace ambiguous labels with zeros.

Before scoring, agree on one-to-one 3D coordinate matching in physical micrometres,
including a justified distance tolerance and treatment of uncertainty and edges.
Report false detections, misses, splits and merges separately, along with reviewed
volume and counts. Do not use matching total counts as the accuracy criterion.
Biological claims require representative protocol-matched samples and independent
evaluation across brains/batches; this public pilot tests the review workflow.
