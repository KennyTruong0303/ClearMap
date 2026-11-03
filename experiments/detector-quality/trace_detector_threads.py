"""Trace native-thread variability with frozen images and seed coordinates."""
import os
os.environ['OMP_NUM_THREADS'] = '1'
import hashlib
import inspect
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from skimage.segmentation import watershed
from ClearMap.ImageProcessing.Experts import Cells
from ClearMap.Analysis.Measurements import maxima_detection as md
from ClearMap.Analysis.Measurements import shape_detection as sd
from ClearMap.Analysis.Measurements import Voxelization as vox

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'test-data'/('thread-trace-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
OUT.mkdir()

def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()

results = []
for name in ('center','right'):
    volume = np.load(ROOT/'test-data/peak-plateau-experiment-v4'/f'{name}.npy')
    corrected = Cells.remove_background(volume, shape=(21,21), form='Disk')
    mask = md.find_maxima(corrected,shape=(11,11,1),threshold=168)
    seeds = np.argwhere(mask)
    weights = np.arange(1,len(seeds)+1)
    expected = vox.voxelize(seeds,shape=volume.shape,weights=weights,processes=1).array.copy()
    fixed_shape = watershed(-corrected,expected,mask=corrected>168)
    for threads in (1,4,8):
        markers,shapes,counts,where_hashes,fixed_hashes,invalid = [],[],[],[],[],[]
        for repeat in range(12):
            found = Cells.ap.where(mask, processes=threads).array.copy()
            where_hashes.append(digest(found))
            assert np.array_equal(found,seeds), 'seed enumeration changed'
            peak_img = vox.voxelize(seeds,shape=volume.shape,weights=weights,processes=threads).array.copy()
            shape = watershed(-corrected,peak_img,mask=corrected>168)
            sizes = sd.find_size(shape,max_label=len(seeds))
            markers.append(digest(peak_img)); shapes.append(digest(shape))
            counts.append(int(((sizes>=5)&(sizes<=500)).sum()))
            invalid.append(int((peak_img>len(seeds)).sum()))
            fixed_hashes.append(digest(watershed(-corrected,expected.copy(),mask=corrected>168)))
            if not np.array_equal(peak_img,expected):
                np.save(OUT/f'{name}_threads{threads}_markers{repeat}.npy',peak_img)
        results.append(dict(region=name,threads=threads,repetitions=12,
            unique_seed_coordinate_arrays=len(set(where_hashes)),
            unique_marker_arrays=len(set(markers)),unique_shape_arrays=len(set(shapes)),
            accepted_counts=counts,unique_shapes_with_frozen_markers=len(set(fixed_hashes)),
            pixels_with_label_above_seed_count=invalid))
    np.save(OUT/f'{name}_fixed_seeds.npy',seeds)
    np.save(OUT/f'{name}_serial_markers.npy',expected)

# Minimal reproduction: two adjacent seeds labelled 1 and 2.
points=np.array([[10,10,0],[11,10,0]],dtype=int)
synthetic=[]
for method in ('radius1','radius0'):
    for threads in (1,4,8):
        arrays=[vox.voxelize(points,shape=(25,25,1),weights=np.array([1,2]),
                 radius=(1,1,1) if method=='radius1' else (0,0,0),processes=threads).array.copy() for _ in range(30)]
        synthetic.append(dict(method=method,threads=threads,repetitions=30,
            unique_arrays=len({digest(a) for a in arrays}),
            labels=sorted({int(v) for a in arrays for v in np.unique(a)})))
report=dict(results=results,synthetic=synthetic,
    runtime_sources={inspect.getfile(m):digest(np.frombuffer(Path(inspect.getfile(m)).read_bytes(),dtype=np.uint8))
                     for m in (Cells,sd,vox)},
    scope='Frozen 2D demo inputs; no installed/source files modified; zero radius is diagnostic only')
(OUT/'report.json').write_text(json.dumps(report,indent=2))
print(str(OUT)); print(json.dumps(report,indent=2))
