"""Read-only source audit; does not normalize or relabel data."""
from pathlib import Path
import hashlib
import json
import numpy as np
import tifffile

root = Path(__file__).resolve().parent / 'test-data/public-cellfinder-3d'
manifest = json.loads((root / 'manifest.json').read_text())
report = {'channels': {}, 'source_hashes_match': True}
for item in manifest['files']:
    path = root / item['path'].replace('\\', '/')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
for ch in (0, 1):
    a = np.load(root / f'ch{ch}_zyx.npy', mmap_mode='r')
    planes = []
    for z in range(len(a)):
        with tifffile.TiffFile(root / f'ch{ch}/ch{ch}{z:04}.tif') as f:
            assert np.array_equal(a[z], f.asarray())
            planes.append({'z': z, 'source_label': f.imagej_metadata.get('Labels'),
                           'median': float(np.median(a[z])),
                           'mean': float(a[z].mean())})
    correlations = [float(np.corrcoef(a[z].ravel(), a[z+1].ravel())[0, 1])
                    for z in range(len(a)-1)]
    report['channels'][str(ch)] = {'planes': planes, 'adjacent_correlations': correlations,
                                   'array_equals_source_tiffs': True}
report['interpretation'] = ('Broad periodic intensity discontinuities are present in source files, '
    'with consecutive embedded source labels. Acquisition versus upstream processing cause is unknown. '
    'Do not infer cell identity or biological activity from the intensity jumps.')
out = root.parent / 'reference-review-v1/plane-continuity-audit.json'
out.write_text(json.dumps(report, indent=2))
print(out)
