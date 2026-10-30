# Peak plateau experiment

Local WSL experiment completed 2026-10-25. No ClearMap source, installed package,
or production configuration was modified. The test script patches functions only
inside its own process. No SSH host was used.

## Result

Seven synthetic checks passed: a connected flat 2x2 maximum becomes one seed;
two disconnected equal peaks remain two; separate flat peaks become two;
single and empty cases remain unchanged. Diagonal ties deliberately remain
separate. Suppressed weaker neighbors are not recovered.

On NEATmap image 25, frame 5, channel 0, threshold 168 and 11x11x1 maxima,
the center crop changes from 98 to 92 seeds and 27 to 25 accepted candidates;
the right crop changes from 55 to 45 seeds and 20 to 18 accepted candidates.
These totals are not accuracy scores or biological cell counts.

The visibly separated pair remains represented, but one object still has two
centers: its equal maxima are disconnected. The crowded cluster changes from
four to three centers; its biological count remains unresolved. Collapsing
connected plateaus is therefore a partial correction, not a complete solution.

## Repeatability

With the original native-thread allocation, three unchanged center-crop runs
returned 27, 26, and 25 accepted candidates. The right crop retained a count of
20 but its accepted rows differed. Seed counts stayed constant.

Forcing detect_cells_block to use one native thread produced identical accepted
rows across three repetitions of each variant in both crops. This implicates
native-thread execution in the variability but does not identify the exact
faulty routine. A worker-process limit alone does not limit those threads.

Use the freshly generated single-thread baseline for this comparison. It matches
the older saved center baseline; the old right baseline is not an exact match.

## Artifacts and next checkpoint

- Experiment: test_peak_plateaus.py (single native thread is now the default).
- Explicit diagnostic opt-in: --native-thread-diagnostic.
- Complete controlled results: test-data/peak-plateau-experiment-v4/report.json
- Visual comparison: test-data/peak-plateau-experiment-v4/comparison.png
- v3 contains the native-thread repeatability comparison.
- Earlier experiment and v2 folders are partial failed-baseline-check attempts.

The script creates a fresh UTC-timestamped output folder for each run and refuses
to overwrite it. Current tests use installed ClearMap; source hashes,
input hash, and library versions are recorded in the report.

Next: review disconnected peaks on single objects and genuinely touching cells
before choosing any broader merge rule. Diagnose native-thread variability
separately before restoring parallelism. Do not promote the experimental
correction to a general detector based on these selected 2D tuning crops.

## Human checkpoint, 2026-10-25

The user reviewed the upper bright object in the second row of the v4 comparison
and judged it to be one cell. This is the right crop near (150,39), approximately
original-image (1550,239), frame 5, channel 0. The original and experimental
detectors both retain centers at crop (149,39) and (151,38), so this remains a
duplicate relative to the user's label. This label is provisional human review,
not independent biological ground truth. The lower object and crowded cluster
were not newly labelled by this answer. The user accepted single-threaded
comparisons while the native-thread variability is investigated.
