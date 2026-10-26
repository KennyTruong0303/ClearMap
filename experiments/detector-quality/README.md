# ClearMap detector-quality experiments

This directory contains the local ClearMap improvement work moved from
C:\dev\iDisco-analysis on 2026-10-26. Analysis projects remain in that repository.

Start with CLEARMAP_IMPROVEMENT_LOG.md for decisions, findings and outstanding
validation. The current priority is investigating unexpected watershed size
changes after seed removal before adopting the experimental 6% merge rule.

Scripts resolve paths relative to this directory. Run them with the existing
ClearMap Python environment in local WSL, for example:

    /home/kenny/miniconda3/envs/clearmap/bin/python /mnt/c/dev/ClearMap-work/experiments/detector-quality/test_shallow_dip.py

test-data/ contains the migrated evidence and verified copies of the two demo
input TIFFs. Large inputs and generated outputs are ignored by Git; scripts and
review notes are versionable. The original analysis input TIFFs were preserved.
Historical reports retain original paths as provenance; their relative output
paths now resolve within this directory. migration-original-hashes.json records
SHA256 values verified during the move, before the two path edits.

The original ClearMap checkout and installed package were not modified.
This is experimental work, not a production detector or completed agent pipeline.

Planned automation uses subscription-backed agent sessions for both pipeline
execution and a separate QC review, followed by human scientific checkpoints.
No OpenAI API key is planned. Local run artifacts will carry evidence and review
decisions; the supported session/handoff mechanism remains to be validated before
implementation. QC is a separate review role, not tied to the Astra model name.
