"""Compare the experimental shallow-dip rule with ClearMap's built-in h_max option.

Seed-stage comparison only; no watershed, size filter or ClearMap source edits.

Default: a synthetic benchmark with known cells, swept over both parameters.
--crop: run every method on a saved demo crop (e.g. the center.npy / right.npy
volumes saved by test_direct_markers.py) and report seeds at the reviewed objects.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent
try:
    import ClearMap  # noqa: F401
except ImportError:
    sys.path.insert(0, str(ROOT.parents[1]))  # fall back to this checkout's ClearMap
import ClearMap.ImageProcessing.GreyReconstruction as gr
try:
    from skimage.morphology._greyreconstruct import reconstruction_loop  # noqa: F401
except ImportError:
    # scikit-image >= 0.20 removed the private loop ClearMap imports; the public
    # function runs the same reconstruction by dilation with a full 3^n neighbourhood.
    from skimage.morphology import reconstruction
    gr.reconstruct = lambda seed, mask=None, **kwargs: reconstruction(seed, mask, method='dilation')
import ClearMap.Analysis.Measurements.maxima_detection as md
import ClearMap.ImageProcessing.Filter.FilterKernel as fk

SHAPE = (11, 11, 1)
THRESHOLD = 168
FRACTIONS = [0, .03, .06, .10, .15, .20, .30]
H_VALUES = [5, 10, 17, 25, 35, 50, 75, 100]
TIEBREAK_SIGMAS = [1.]  # in-plane Gaussian sigma (pixels) of the tie-break signal
DOG_SHAPES = [5, 7, 9]  # in-plane dog_filter shape, kernel (s, s, 1)
BANDS = [('dim', 0, 400), ('mid', 400, 800), ('bright', 800, np.inf)]
VOXEL_UM = np.array([2., 2., 5.])  # x, y, z; as in the BrainGlobe cellfinder sample
SHAPE_3D = (96, 96, 24)  # voxels: 192 x 192 x 120 micrometres
CELLS_3D = 150
# Noise regimes: additive sigma (intensity units), multiplicative texture amplitude and
# intensity step. Every NEATmap value quoted in the review notes (304, 288, 400, 272, 32)
# is a multiple of 16, as 12-bit data stored in 16 bits would be; background removal
# by opening keeps that step, and the coarse step is what makes exactly tied peaks common.
REGIMES = {'additive_step16': dict(noise=12., texture=.04, step=16),
           'texture_step16': dict(noise=3., texture=.15, step=16),
           'additive_continuous': dict(noise=12., texture=.04, step=0)}
# Reviewed objects from test_shallow_dip.py; each was judged to be one object.
REVIEWED = {'right': [(150, 39, 'Reviewed upper object'), (163, 51, 'Separate lower neighbor'), (190, 170, 'C')],
            'center': [(113, 43, 'Reviewed center 1'), (33, 138, 'Reviewed center 2'), (98, 113, 'Reviewed center 3')]}


def collapse_plateaus(source, mask):
    """Copied from test_peak_plateaus.py."""
    result = np.zeros_like(mask, dtype=bool)
    for value in np.unique(source[mask]):
        labels, count = ndi.label(mask & (source == value))
        for label in range(1, count + 1):
            coords = np.argwhere(labels == label)
            distance = ((coords - coords.mean(axis=0)) ** 2).sum(axis=1)
            result[tuple(coords[np.argmin(distance)])] = True
    return result


def merge(image, seeds, fraction, threshold=THRESHOLD):
    """Copied from test_shallow_dip.py, returning the retained seeds only."""
    order = sorted(range(len(seeds)), key=lambda i: (-float(image[tuple(seeds[i])]), tuple(seeds[i])))
    kept = []
    for i in order:
        p = tuple(seeds[i]); floor = float(image[p]) * (1 - fraction)
        labels, _ = ndi.label((image >= floor) & (image > threshold))
        component = labels[p]
        if not any(component and labels[tuple(seeds[j])] == component for j in kept):
            kept.append(i)
    return np.array(sorted(seeds[i].tolist() for i in kept), dtype=int).reshape(-1, image.ndim)


def baseline_seeds(image, shape=SHAPE):
    return np.argwhere(collapse_plateaus(image, md.find_maxima(image, h_max=None, shape=shape, threshold=THRESHOLD)))


def dip_seeds(image, fraction, shape=SHAPE):
    return merge(image, baseline_seeds(image, shape), fraction)


def hmax_seeds(image, h, as_shipped=False, full_connectivity=False, shape=SHAPE):
    """Cells.detect_cells_block's h_max path: h-max maxima, label, centre of mass.

    as_shipped=True uses md.find_center_of_maxima unchanged, which passes
    np.arange(1, n_label) and so drops the last label. Default counts every label.
    find_center_of_maxima labels with face connectivity, which splits flattened
    plateaus that touch only diagonally; full_connectivity=True labels with 3^n.
    """
    structure = np.ones((3,) * image.ndim) if full_connectivity else None
    labels, n = ndi.label(md.find_maxima(image, h_max=h, shape=shape, threshold=THRESHOLD), structure=structure)
    if as_shipped:
        centers = md.find_center_of_maxima(image, label=labels)
    else:
        centers = np.array(ndi.center_of_mass(image, labels, np.arange(1, n + 1)))
    return np.rint(centers).astype(int).reshape(-1, image.ndim)


def dog_filter(source, shape):
    """Cells.dog_filter with its default sigmas (Cells needs cv2, so it is not imported)."""
    filtered = ndi.correlate(source, fk.filter_kernel(ftype='dog', shape=shape).astype('float32'))
    filtered[filtered < 0] = 0
    return filtered


def filtered_seeds(image, filtered, shape=SHAPE):
    """Baseline seeds found on a filtered image, thresholded on the unfiltered one.

    The DoG output is not in intensity units, so the detection threshold stays
    on the background-corrected image and only the choice of maxima changes.
    """
    mask = md.find_maxima(filtered, h_max=None, shape=shape, threshold=None) & (image >= THRESHOLD)
    return np.argwhere(collapse_plateaus(filtered, mask))


def tiebreak(image, sigma):
    """The image plus under 0.5 units of its smoothed self: exact ties are broken
    by the neighbourhood, and every other intensity order is kept."""
    smooth = ndi.gaussian_filter(image, (sigma, sigma, 0))
    return image + .5 * smooth / (smooth.max() + 1)


def methods():
    yield 'baseline', None, baseline_seeds
    for s in TIEBREAK_SIGMAS:
        yield 'tiebreak', s, lambda image, s=s: filtered_seeds(image, tiebreak(image, s))
    for s in DOG_SHAPES:
        yield 'dog', s, lambda image, s=s: filtered_seeds(image, dog_filter(image, (s, s, 1)))
    for f in FRACTIONS[1:]:
        yield 'dip', f, lambda image, f=f: dip_seeds(image, f)
    for h in H_VALUES:
        yield 'h_max', h, lambda image, h=h: hmax_seeds(image, h)
    for h in H_VALUES:
        yield 'h_max_full', h, lambda image, h=h: hmax_seeds(image, h, full_connectivity=True)


def scene(rng, regime, size=128, n_cells=45):
    """Gaussian cells with smooth multiplicative texture plus additive noise.

    Returns the noisy image, the noise-free image (texture included: it is real
    structure inside a cell), per-cell amplitudes and a map of the dominant cell.
    """
    sigma = rng.uniform(1.4, 2.4, n_cells)
    amplitude = np.exp(rng.uniform(np.log(200), np.log(1500), n_cells))
    centers = []
    while len(centers) < n_cells:
        c = rng.uniform(6, size - 6, 2)
        if all(np.hypot(*(c - d)) > 4.5 for d in centers):  # cells may touch, never coincide
            centers.append(c)
    yy, xx = np.mgrid[:size, :size]
    texture = ndi.gaussian_filter(rng.normal(size=(size, size)), 1.0)
    texture /= texture.std()
    contributions = np.stack([a * np.exp(-((xx - c[0]) ** 2 + (yy - c[1]) ** 2) / (2 * s ** 2))
                              for a, c, s in zip(amplitude, centers, sigma)])
    clean = contributions.sum(0) * (1 + REGIMES[regime]['texture'] * texture)
    noisy = clean + rng.normal(0, REGIMES[regime]['noise'], clean.shape)
    step = REGIMES[regime]['step']
    if step:
        noisy = np.maximum(np.floor(noisy / step) * step, 0)
    owner = np.where(contributions.max(0) >= .1 * amplitude[contributions.argmax(0)], contributions.argmax(0), -1)
    return noisy.T[:, :, None], clean.T[:, :, None], amplitude, owner.T[:, :, None]


def scene3d(rng, regime, shape=SHAPE_3D, n_cells=CELLS_3D):
    """Anisotropic 3D version of scene(): cells are round in micrometres, so they
    span about two to four 5-micrometre planes. Same amplitudes, texture and noise."""
    sigma = rng.uniform(2.8, 4.8, n_cells)[:, None] / VOXEL_UM  # 1.4-2.4 px in XY, as in 2D
    amplitude = np.exp(rng.uniform(np.log(200), np.log(1500), n_cells))
    extent = np.array(shape) * VOXEL_UM
    margin = np.array([12., 12., 10.])
    centers = []
    while len(centers) < n_cells:
        c = rng.uniform(margin, extent - margin)
        if all(np.linalg.norm(c - d) > 9 for d in centers):  # 9 um, as 4.5 px in 2D
            centers.append(c)
    total = np.zeros(shape); best = np.zeros(shape); owner = np.full(shape, -1)
    for i, (a, c, s) in enumerate(zip(amplitude, np.array(centers) / VOXEL_UM, sigma)):
        lo = np.maximum(np.floor(c - 4 * s).astype(int), 0)
        hi = np.minimum(np.ceil(c + 4 * s).astype(int) + 1, shape)
        box = tuple(slice(l, h) for l, h in zip(lo, hi))
        grid = np.ogrid[box]
        g = a * np.exp(-sum((x - ci) ** 2 / (2 * si ** 2) for x, ci, si in zip(grid, c, s)))
        total[box] += g
        win = g > best[box]
        best[box] = np.where(win, g, best[box]); owner[box] = np.where(win, i, owner[box])
    owner = np.where((owner >= 0) & (best >= .1 * amplitude[owner]), owner, -1)
    texture = ndi.gaussian_filter(rng.normal(size=shape), (1, 1, .4))
    texture /= texture.std()
    clean = total * (1 + REGIMES[regime]['texture'] * texture)
    noisy = clean + rng.normal(0, REGIMES[regime]['noise'], shape)
    step = REGIMES[regime]['step']
    if step:
        noisy = np.maximum(np.floor(noisy / step) * step, 0)
    return noisy, clean, amplitude, owner


def methods3d():
    """In-plane windows of 11 (Codex's 2D setting, +-10 um) and 5 (ClearMap's
    default, +-4 um) pixels, by 1, 3 or 5 planes (+-0, 5, 10 um in Z)."""
    for w, zs in ((11, (1, 3, 5)), (5, (1, 3))):
        for z in zs:
            yield f'baseline_w{w}_z{z}', None, lambda image, w=w, z=z: baseline_seeds(image, (w, w, z))
    for f in (.06, .10):
        yield 'dip_w11_z1', f, lambda image, f=f: dip_seeds(image, f, (11, 11, 1))
    yield 'dip_w11_z3', .10, lambda image: dip_seeds(image, .10, (11, 11, 3))
    yield 'dip_w5_z1', .10, lambda image: dip_seeds(image, .10, (5, 5, 1))
    for w, z in ((11, 1), (11, 3), (5, 1)):
        yield f'h_max_full_w{w}_z{z}', 17, lambda image, w=w, z=z: hmax_seeds(image, 17, full_connectivity=True, shape=(w, w, z))
    yield 'tiebreak_w11_z3', 1., lambda image: filtered_seeds(image, tiebreak(image, 1.), (11, 11, 3))
    yield 'dog_w11_z3', 7, lambda image: filtered_seeds(image, dog_filter(image, (7, 7, 3)), (11, 11, 3))
    for k in (7, 5):
        for z in (1, 3):
            yield f'dog_w5_z{z}', k, lambda image, k=k, z=z: filtered_seeds(image, dog_filter(image, (k, k, 3)), (5, 5, z))


def score(seeds, owner, n_cells):
    """Seeds per cell, plus seeds that fall on no cell."""
    hits = owner[tuple(seeds.T)] if len(seeds) else np.array([], int)
    return np.bincount(hits[hits >= 0], minlength=n_cells), int((hits < 0).sum())


def benchmark(n_scenes, seed, dims=2, only=None):
    rows = []
    for regime in REGIMES:
        rng = np.random.default_rng(seed)
        totals = {}
        for _ in range(n_scenes):
            if dims == 2:
                noisy, clean, amplitude, owner = scene(rng, regime)
                # Score only cells that are separable in the noise-free image.
                scorable = score(baseline_seeds(clean), owner, len(amplitude))[0] >= 1
            else:
                noisy, clean, amplitude, owner = scene3d(rng, regime)
                # In 3D the window itself is under test, so a cell is scorable when the
                # noise-free image has a 3x3x3 local maximum above threshold on it.
                peaks = (ndi.maximum_filter(clean, size=3) == clean) & (clean >= THRESHOLD)
                scorable = score(np.argwhere(peaks), owner, len(amplitude))[0] >= 1
            for name, value, find in (methods() if dims == 2 else methods3d()):
                if only and not any(name.startswith(prefix) for prefix in only):
                    continue
                per_cell, stray = score(find(noisy), owner, len(amplitude))
                for band, lo, hi in BANDS:
                    sel = scorable & (amplitude >= lo) & (amplitude < hi)
                    t = totals.setdefault((name, value, band), dict(cells=0, extra=0, lost=0, stray=0))
                    t['cells'] += int(sel.sum())
                    t['extra'] += int(np.maximum(per_cell[sel] - 1, 0).sum())
                    t['lost'] += int((per_cell[sel] == 0).sum())
                t['stray'] += stray  # stray seeds are not banded; kept on the last band row
        for (name, value, band), t in totals.items():
            rows.append(dict(regime=regime, method=name, value=value, band=band, cells=t['cells'],
                             extra_per_100=round(100 * t['extra'] / t['cells'], 2),
                             lost_per_100=round(100 * t['lost'] / t['cells'], 2),
                             stray=t['stray'] if band == BANDS[-1][0] else None))
    return rows


def profiles():
    """Codex's synthetic and adversarial cases, with seeds supplied as Codex did."""
    cases = [('one_object_shallow_ripple', (9, 3, 1), (1, 1, 0), (7, 1, 0), 288, (304, 304), 1),
             ('two_deep_separated_peaks', (9, 3, 1), (1, 1, 0), (7, 1, 0), 180, (304, 304), 2),
             ('touching_unequal_peaks_deep_valley', (9, 3, 1), (1, 1, 0), (7, 1, 0), 180, (400, 240), 2),
             ('two_objects_shallow_valley_ambiguity', (9, 3, 1), (1, 1, 0), (7, 1, 0), 232, (400, 240), 2),
             ('long_bright_bridge_two_objects', (31, 9, 1), (3, 4, 0), (27, 4, 0), 288, (304, 304), 2),
             ('unequal_touching_shallow_saddle', (31, 9, 1), (3, 4, 0), (27, 4, 0), 232, (400, 240), 2),
             ('unequal_touching_deep_saddle', (31, 9, 1), (3, 4, 0), (27, 4, 0), 190, (400, 240), 2),
             ('single_object_deeper_texture', (31, 9, 1), (3, 4, 0), (12, 4, 0), 280, (304, 304), 1)]
    out = []
    for name, shape, p, q, bridge, peaks, expected in cases:
        a = np.zeros(shape)
        a[p[0]:q[0] + 1, p[1], 0] = bridge
        a[p], a[q] = peaks
        # Dip rule on the supplied seeds, as Codex ran it; h_max through the full
        # pipeline path, so the 11x11 maxima window applies as it would in ClearMap.
        out.append(dict(case=name, expected=expected, baseline=len(baseline_seeds(a)),
                        dip_6pct=len(merge(a, np.array([p, q]), .06)),
                        **{f'h_max_{h}': len(hmax_seeds(a, h)) for h in (17, 25)},
                        **{f'h_max_full_{h}': len(hmax_seeds(a, h, full_connectivity=True)) for h in (17, 25)}))
    return out


def real_crop(path, region, corrected):
    volume = np.load(path).astype(float)
    if not corrected:
        from ClearMap.ImageProcessing.Experts import Cells
        volume = Cells.remove_background(volume, shape=(21, 21), form='Disk').astype(float)
    report = []
    for x, y, title in REVIEWED[region]:
        row = dict(object=title, crop_xy=[x, y])
        for name, value, find in methods():
            seeds = find(volume)
            near = seeds[(np.abs(seeds[:, 0] - x) <= 6) & (np.abs(seeds[:, 1] - y) <= 6)]
            row[name if value is None else f'{name}_{value}'] = len(near)
        report.append(row)
    totals = {name if value is None else f'{name}_{value}': len(find(volume)) for name, value, find in methods()}
    return dict(region=region, path=str(path), seeds_near_reviewed_objects=report, total_seeds=totals)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenes', type=int, default=120)
    parser.add_argument('--seed', type=int, default=20261029)
    parser.add_argument('--crop', type=Path, help='Saved x,y,z crop volume (.npy)')
    parser.add_argument('--region', choices=list(REVIEWED), help='Which reviewed objects the crop holds')
    parser.add_argument('--corrected', action='store_true', help='Crop is already background-corrected')
    parser.add_argument('--dims', type=int, choices=[2, 3], default=2, help='Synthetic benchmark in 2D or anisotropic 3D')
    parser.add_argument('--methods', nargs='+', help='Run only methods whose names start with these prefixes; '
                        'scenes depend only on --seed, so results stay comparable with a full run')
    args = parser.parse_args()
    out = ROOT / 'test-data' / ('dip-vs-hmax-' + ('3d-' if args.dims == 3 else '') + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    out.mkdir(parents=True, exist_ok=False)

    # The shipped h_max path drops the last maximum: two maxima in, one centre out.
    two = np.zeros((30, 9, 1)); two[5, 4, 0], two[20, 4, 0] = 300, 250
    report = dict(shipped_hmax_centres_for_two_maxima=len(hmax_seeds(two, 17, as_shipped=True)),
                  fixed_hmax_centres_for_two_maxima=len(hmax_seeds(two, 17)),
                  parameters=dict(maxima_shape=SHAPE, threshold=THRESHOLD, regimes=REGIMES,
                                  bands=[b[:2] for b in BANDS], scenes_per_regime=args.scenes, seed=args.seed))
    if args.crop:
        if not args.region:
            parser.error('--crop needs --region')
        report['real_crop'] = real_crop(args.crop, args.region, args.corrected)
    else:
        if args.dims == 3:
            report['parameters'].update(voxel_xyz_um=VOXEL_UM.tolist(), volume=SHAPE_3D, cells_per_scene=CELLS_3D)
        else:
            report['profiles'] = profiles()
        report['benchmark'] = benchmark(args.scenes, args.seed, args.dims, args.methods)
    (out / 'report.json').write_text(json.dumps(report, indent=2, default=float))
    print(out)
    print(json.dumps({k: v for k, v in report.items() if k != 'benchmark'}, indent=2, default=float))


if __name__ == '__main__':
    main()
