# CANVAS documentation/access audit — 2026-10-27

Status: documentation inspected; no dataset downloaded, license accepted, or detector run.

Primary sources:
- https://arxiv.org/html/2603.29842v1 (sections3.1,3.2,4.1,4.2.1,6.4)
- https://canvas.lightsheetdata.com/
- https://canvas.lightsheetdata.com/data (live portal inspected)

## Scientific suitability
Documented XYZ acquisition spacing1.8x1.8x4 micrometres. SHIELD preservation,
SmartBatch+ labeling, EasyIndex matching, SmartSPIM imaging; not an iDISCO protocol
match. Processing includes destriping, stitching and flat-field correction.
Public annotations are CSV individual cell centers (id,x,y,z,label); label column
is not used in evaluation. Authors describe manual false-positive review and
recovery of missed cells, with model-assisted initial candidates.

cFos brain_8 is a hemisphere, listed70GB. Public TRAIN ROIs:
- region1: origin(4076,4422,899), size500x500x250,3782 cells.
- region2: origin(4402,3198,1132), size300x300x150,2827 cells.
- region3: origin(2481,5237,484), size400x400x200,2781 cells.
Portal gives ROI coordinates but actual CSV coordinate conventions still need
verification. Official TEST annotations/regions are withheld (10619 cFos cells).
No local published-test evaluation can be claimed from the public training ROIs.
Raw file spacing, continuity and annotation alignment remain untested.

## Access limitation relevant to planned deployment
Live data portal displays CANVAS Dataset License Agreement v1.0 December2025.
It states download/access/use binds the user, limits use to non-commercial
purposes, prohibits dataset redistribution and prohibits deployment of Dataset
or Derivative Works in Production Systems. Its definition of derivative works
includes analyses, software, algorithms, parameters, outputs and results. Production
Systems includes delivery of analysis/results to third parties without requiring
payment. This warrants provider clarification for the intended server workflow;
do not silently accept it or assume ordinary academic use resolves the issue.
Contact shown: data@lifecanvastech.com. No contact sent or authorized specifically
for CANVAS. No download buttons activated.

Recommendation: keep CANVAS as a documented candidate, not the selected development
dataset, pending acceptable usage terms and an accessible small image/annotation
subset. DELiVR clarification remains pending dispatch via user's email service.

## Access follow-up — 2026-10-27
User explicitly accepted the displayed CANVAS agreement and authorized proceeding.
Browser approval initially failed due to usage limit; normal retry on user request
succeeded. cFOS Download opens Request Data Access form requiring first name,
last name, email and institution/organization. Awaiting user-provided submission
details. No form submitted and no dataset downloaded. DELiVR clarification request
was sent by the user, per their report.

## Access granted — 2026-10-27
After explicit confirmation of submission details, CANVAS registration was submitted
successfully. The request modal closed and the cFos_brain_8 download directory became
available, exposing image/, label/, LICENSE.md and a76325611520-byte full archive.
Screenshot: test-data/canvas-access-confirmed.png. No full archive downloaded.
Next: inspect label files and individual image access for a bounded subset audit.

## First downloaded subset audit
Downloaded official TRAIN region2 CSV and planes1133-1135 (~202MB); official TEST
folder not opened. Script audit_canvas_subset.py records hashes/metadata and emits
alignment-qc.png plus300x300x3 crop under ignored test-data/canvas-audit/.
CSV has2827 distinct IDs and2827 distinct XYZ coordinates, matching portal count.
Coordinates span(4401,3198,1132)..(4702,3498,1282): some fall just outside the
published half-open ROI bounds. Retain all labels; boundary convention unresolved.
All TIFFs decode as uint16 YX,10258x5599; headers lack physical units. Paper-derived
XYZ spacing1.8/1.8/4um remains an external calibration, not header-confirmed.
Using global XY and filename-prefix Z gives visually plausible cell-center overlays.
Exact zero/one-based indexing remains a hypothesis pending stronger checks.
Cropped medians345/346/346, adjacent correlations0.881/0.892; no abrupt broad jump
visible in these three planes. This is only a preliminary continuity check, not a
full-depth audit or biological accuracy evaluation. No detector or tuning run.
Next: expand contiguous training-region depth with halo, resolve edge/index rules,
and verify annotation alignment throughout the crop before baseline scoring.

## Expanded audit in progress
Selected contiguous filename prefixes1130..1141 with20-pixel XY context around
region2. Nine additional full planes are required. WSL HTTP request returned403;
Windows download route is working, staging files with .part suffix until complete.
Audit script extend_canvas_audit.py requires all12 decoded planes before reporting.
Boundary labels: X lower4401 (1), X upper4702 (15), Y upper3498 (8), Z upper1282 (16).
These40 labels remain preserved. An inclusive upper boundary explains39, but not
all; no global indexing correction can be concluded from this alone. Compare
small coordinate shifts diagnostically, without changing source labels or choosing
a correction just to maximize signal. Use image context beyond annotation bounds
for preprocessing only; unannotated context must not count as reference negatives.

## Expanded audit results — 2026-10-30
All12 requested planes1130..1141 completed and decoded successfully. Local SHA256
fingerprints saved (these provide reproducibility, not independently published
checksum verification). Expanded crop shapeZYX12x340x340, originXYZ4382/3178/1130.
Plane medians347,347,347,347,347,347,347,346,345,344,343,342. Adjacent correlations
0.853..0.891; no abrupt broad intensity/spatial jump seen in inspected montage.
Evidence: test-data/canvas-audit/expanded-audit.json and expanded-alignment.png.
For138 labeled centers across prefixes1133..1138, unchanged coordinates have median
intensity631; best tested +/-1-voxel shift(0,-1,0) gives633. This small difference
is not evidence of an indexing correction. Supplied coordinates remain unchanged;
visual alignment supports their use as a provisional mapping, not exact index proof.
Boundary discrepancy confirmed:39 at nominal upper limits and1 at lowerX-1.
Keep complete original CSV and explicitly report boundary ambiguity. For a future
local pilot, score only a predeclared interior core and exclude ambiguous region
edges from both prediction/reference scoring; context outside labels is not negative
reference. No boundary convention silently inferred, no reference cells deleted.
The12-plane sample is suitable for preliminary input/coordinate checks, but does
not establish sufficient preprocessing overlap or full-object Z extent. More depth
or a validated support-based halo is necessary before biological count scoring.
No ClearMap detection, threshold tuning, or official TEST access performed.
