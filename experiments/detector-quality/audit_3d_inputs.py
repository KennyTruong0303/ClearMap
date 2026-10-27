"""Record local input metadata without reinterpreting time as spatial depth."""
import json
import hashlib
from pathlib import Path
from datetime import datetime,timezone
import tifffile

root=Path(__file__).resolve().parent
out=root/'test-data'/('3d-input-audit-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
out.mkdir()
records=[]
for number in [25,26]:
    path=root/f'test-data/neatmap/RawImage_example/RawImage_merged_{number}.tif'
    with tifffile.TiffFile(path) as tf:
        meta=tf.imagej_metadata or {}
        records.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            series=[dict(shape=s.shape,axes=s.axes) for s in tf.series],
            imagej={k:meta[k] for k in ['frames','channels','slices','spacing','unit'] if k in meta},
            spatial_z_verified=False,decision='Do not reinterpret T as Z without acquisition provenance'))
atlas=Path('/home/kenny/iDisco-analysis/test-data/atlas-demo/sample_50um_asr.tif')
if atlas.exists():
    with tifffile.TiffFile(atlas) as tf:
        records.append(dict(path=str(atlas),shape=tf.series[0].shape,axes=tf.series[0].axes,
            decision='Existing coarse registration demo; not selected for cell-resolution validation',
            provenance_note='Local preparation script describes resampling to 50um; not independent biological cell labels'))
(out/'report.json').write_text(json.dumps(records,indent=2))
print(out); print(json.dumps(records,indent=2))
