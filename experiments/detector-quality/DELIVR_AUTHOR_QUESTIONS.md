# Draft clarification request — not sent

Subject: DELiVR public c-Fos patches: calibration and published evaluation split

Hello,

We are preparing an independent ClearMap cell-counting evaluation using the
public DELiVR c-Fos reference data and want to preserve your published test split.
Could you help clarify the following?

1. Which filenames comprise the published nine test patches and 39 training
   patches? The v1.0.0 release contains 48 raw patches but 41 ground-truth masks.
   Are the seven absent masks available elsewhere?
2. What are the physical voxel spacings and microscope-axis order of the exported
   NIfTI patches? The sampled headers contain unit zooms and unknown units. Are
   they unresampled acquisition data at XYZ 1.625 x 1.625 x 6 micrometres, or were
   they resampled/reoriented during export?
3. Are original individual-cell IDs or centroids available? The sampled masks are
   binary, and cell_analysis.py derives reference instances using connected
   components. How should touching cells, fragments and boundary objects be handled?
4. In patchvolume_1008_0.nii.gz, array axis 2 changes sharply between indices 10
   and 11 (zero-based). Both images and masks were verified against repository
   hashes. Is this expected acquisition structure, an export ordering effect, or
   a known issue? Is a patch-to-original-volume coordinate map available?

Files inspected: raw/gt patchvolume_1008_0.nii.gz and patchvolume_1147_0.nii.gz.
Release: erturklab/delivr_cfos v1.0.0, commit
b12b003a0ac32a23314486fa6e20d35173baf579. Their Git blobs match current commit
51ef796da883ace0afbbf589630b0e756dd3c6d3.

Thank you for making the data available. We have not tuned on or evaluated these
patches while clarifying their provenance and split membership.
