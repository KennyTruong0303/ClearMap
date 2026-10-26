"""Isolated plateau experiment; no ClearMap source or default settings are edited."""
import copy
import argparse
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path

os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np
import pandas as pd
import scipy
from scipy import ndimage as ndi
import tifffile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ClearMap.ImageProcessing.Experts import Cells
from ClearMap.Analysis.Measurements import maxima_detection as md

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
thread_mode = parser.add_mutually_exclusive_group()
thread_mode.add_argument('--single-native-thread', action='store_true', help='Use the default controlled single-thread mode')
thread_mode.add_argument('--native-thread-diagnostic', action='store_true', help='Explicitly opt into original native-thread allocation for diagnosis')
args = parser.parse_args()
SINGLE_NATIVE_THREAD = not args.native_thread_diagnostic
run_stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = ROOT / 'test-data' / f'peak-plateau-{run_stamp}'
ORIGINAL = md.find_maxima
ORIGINAL_BLOCK = Cells.detect_cells_block


def single_thread_block(source, parameter=Cells.default_cell_detection_parameter, n_threads=None):
    return ORIGINAL_BLOCK(source, parameter=parameter, n_threads=1)


def collapse_plateaus(source, mask):
    """One existing pixel per face-connected, equal-value maximum plateau.

    Equal-valued but disconnected peaks remain independent. No distance-based
    merging and no interpolation or change to the underlying image.
    """
    result = np.zeros_like(mask, dtype=bool)
    for value in np.unique(source[mask]):
        labels, count = ndi.label(mask & (source == value))
        for label in range(1, count + 1):
            coords = np.argwhere(labels == label)
            distance = ((coords - coords.mean(axis=0)) ** 2).sum(axis=1)
            point = coords[np.argmin(distance)]
            result[tuple(point)] = True
    return result


def experimental_maxima(source, h_max=None, shape=5, threshold=None, verbose=None):
    if h_max is not None:
        raise ValueError('This experiment only tests h_max=None')
    mask = ORIGINAL(source, h_max=h_max, shape=shape, threshold=threshold, verbose=verbose)
    return collapse_plateaus(source, mask)


def synthetic_tests():
    cases = []
    for name, points, expected_before, expected_after in [
        ('single_peak', [(10, 10, 100)], 1, 1),
        ('flat_2x2_peak', [(10,10,100),(10,11,100),(11,10,100),(11,11,100)], 4, 1),
        ('two_equal_separate_peaks', [(10,10,100),(13,10,100)], 2, 2),
        ('two_separate_flat_peaks', [(10,10,100),(10,11,100),(13,10,100),(13,11,100)], 4, 2),
        ('weaker_neighbor_already_suppressed', [(10,10,100),(13,10,80)], 1, 1),
        ('diagonal_tie_kept_separate', [(10,10,100),(11,11,100)], 2, 2),
        ('empty', [], 0, 0),
    ]:
        a = np.zeros((25,25,1), dtype=np.uint16)
        for x,y,v in points:
            a[x,y,0] = v
        mask = ORIGINAL(a, shape=(11,11,1), threshold=50)
        revised = collapse_plateaus(a, mask)
        before, after = int(mask.sum()), int(revised.sum())
        assert (before,after) == (expected_before,expected_after), name
        assert not np.any(revised & ~mask), name
        cases.append(dict(name=name, before=before, after=after, passed=True))
    return cases


def run():
    OUT.mkdir(parents=True, exist_ok=False)
    if SINGLE_NATIVE_THREAD:
        Cells.detect_cells_block = single_thread_block
    tests = synthetic_tests()
    source = ROOT / 'test-data/neatmap/RawImage_example/RawImage_merged_25.tif'
    data = tifffile.imread(source)[5,0]
    regions = [('center',800,200),('right',1400,200)]
    tables, crops, summary = {}, {}, []
    for name,x0,y0 in regions:
        crop = data[y0:y0+256,x0:x0+256]
        crops[name] = crop
        volume = np.asfortranarray(crop.T[:,:,None])
        path = OUT / (name + '.npy')
        np.save(path, volume)
        corrected = Cells.remove_background(volume, shape=(21,21), form='Disk')
        for variant in ['baseline','baseline_repeat1','baseline_repeat2',
                        'plateau_collapsed','plateau_repeat1','plateau_repeat2']:
            p = copy.deepcopy(Cells.default_cell_detection_parameter)
            p.update(illumination_correction=None,equalization=None,dog_filter=None)
            p['background_correction']['shape'] = (21,21)
            p['maxima_detection'].update(shape=(11,11,1),threshold=168,h_max=None)
            p['shape_detection']['threshold'] = 168
            p['intensity_detection']['measure'] = ['source']
            md.find_maxima = ORIGINAL if variant.startswith('baseline') else experimental_maxima
            mask = md.find_maxima(corrected, shape=(11,11,1), threshold=168)
            np.save(OUT / f'{name}_{variant}_seed_mask.npy', mask)
            try:
                cells = Cells.detect_cells(str(path),sink=None,cell_detection_parameter=p,
                    processing_parameter=dict(processes=1,size_min=1,size_max=1,overlap=0,
                                              axes=[2],optimization=False,verbose=False))
            finally:
                md.find_maxima = ORIGINAL
            df = pd.DataFrame(cells)
            df['accepted'] = df['size'].between(5,500)
            df['original_x_pixel'], df['original_y_pixel'] = df.x+x0, df.y+y0
            df.to_csv(OUT / f'{name}_{variant}.csv',index=False)
            tables[name,variant] = df[df.accepted]
            old = (ROOT / 'test-data/neatmap/detection_tuning') / f'{name}_maxima11.csv'
            matches = None
            if variant == 'baseline' and old.exists():
                previous = pd.read_csv(old)
                matches = dict(all_candidates=df.equals(previous),
                               previous_candidates=len(previous),current_candidates=len(df))
                matches['accepted_candidates_match'] = np.array_equal(
                    df[df.accepted][['x','y','z','size','source']].to_numpy(),
                    previous[previous.accepted][['x','y','z','size','source']].to_numpy())
            summary.append(dict(region=name,variant=variant,seeds=int(mask.sum()),
                                accepted=int(df.accepted.sum()),baseline_matches_saved=matches))

    rois = [('center','Three reviewed objects',20,125,25,150),
            ('right','Two visibly separated objects',130,180,20,65),
            ('right','Ambiguous crowded cluster',40,80,115,145),
            ('right','Irregular object / possible touching objects',95,125,95,125)]
    fig,axes = plt.subplots(4,3,figsize=(10,12),constrained_layout=True)
    roi_counts = []
    for row,(region,title,x1,x2,y1,y2) in enumerate(rois):
        crop = crops[region]
        lo,hi = np.percentile(crop,[1,99.8])
        counts = {}
        for col,variant in enumerate(['original','baseline','plateau_collapsed']):
            ax = axes[row,col]
            ax.imshow(crop,cmap='gray',vmin=lo,vmax=hi,interpolation='nearest')
            ax.set_xlim(x1,x2); ax.set_ylim(y2,y1)
            ax.set_xlabel('Crop X (pixels)'); ax.set_ylabel('Crop Y (pixels)')
            if variant != 'original':
                df = tables[region,variant]
                df = df[df.x.between(x1,x2) & df.y.between(y1,y2)]
                counts[variant] = len(df)
                ax.scatter(df.x,df.y,s=110,facecolors='none',edgecolors='lime',linewidths=1)
            ax.set_title(title if col==0 else f'{"Original detector" if col==1 else "Plateau correction"}\n{len(df)} accepted centers',fontsize=10)
        roi_counts.append(dict(region=region,title=title,counts=counts))
    fig.suptitle('Fixed threshold 168 and 11x11 peaks: collapse connected equal-value plateaus only')
    fig.savefig(OUT/'comparison.png',dpi=150)
    source_files = [inspect.getfile(Cells),inspect.getfile(md)]
    report = dict(single_native_thread=SINGLE_NATIVE_THREAD,synthetic_tests=tests,runs=summary,roi_counts=roi_counts,
        source=str(source),frame=5,channel=0,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        runtime_sources={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in source_files},
        versions=dict(numpy=np.__version__,scipy=scipy.__version__),
        repeatability={region:{variant: all(np.array_equal(
            tables[region,variant][['x','y','z','size','source']].to_numpy(),
            tables[region,prefix+str(i)][['x','y','z','size','source']].to_numpy()) for i in (1,2))
            for variant,prefix in [('baseline','baseline_repeat'),('plateau_collapsed','plateau_repeat')]}
            for region,_,_ in regions},
        limitations=['2D exploratory test; not validated cell counts',
          'Face-connected plateaus only; disconnected equal peaks are not merged',
          'Cannot recover weaker peaks already suppressed by the maximum filter',
          'No claim of biological accuracy; selected crops are tuning examples'])
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    run()
