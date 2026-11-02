"""Audit bounded additional Z context, preserving the original crop."""
from pathlib import Path
import json, hashlib
import numpy as np
import tifffile
ROOT=Path(__file__).resolve().parent/'test-data/canvas-audit'
names=sorted(json.loads((ROOT/'depth20-source-list.json').read_text(encoding='utf-8-sig')))
assert [int(n.split('_')[0]) for n in names]==list(range(1126,1146))
planes=[]; records=[]
for name in names:
    path=ROOT/name
    with tifffile.TiffFile(path) as tf:
        a=tf.asarray()
        assert a.shape==(10258,5599) and a.dtype==np.uint16
        planes.append(a[3178:3518,4382:4722].copy())
    records.append(dict(file=name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
volume=np.stack(planes)
assert np.array_equal(volume[4:16],np.load(ROOT/'expanded-zyx.npy'))
report=dict(origin_xyz=[4382,3178,1126],shape_zyx=list(volume.shape),files=records,
    original_12_planes_exact=True,spacing='Paper XYZ 1.8/1.8/4 micrometers; no new calibration claim',
    medians=[float(np.median(p)) for p in volume],
    adjacent_correlations=[float(np.corrcoef(p.ravel(),q.ravel())[0,1]) for p,q in zip(volume[:-1],volume[1:])])
np.save(ROOT/'depth20-zyx.npy',volume)
(ROOT/'depth20-audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
