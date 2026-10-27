"""Acquire two pinned DELiVR pairs for data QA only; no detector execution."""
from pathlib import Path
import json, hashlib, urllib.request
import numpy as np
import nibabel as nib
from scipy import ndimage

ROOT = Path(__file__).resolve().parent / 'test-data/delivr-audit'
COMMIT = '51ef796da883ace0afbbf589630b0e756dd3c6d3'
tree = json.loads((ROOT/'source-tree.json').read_text(encoding='utf-8-sig'))
items = {x['path']: x for x in tree['tree'] if x['type']=='blob'}
raw = {Path(p).name for p in items if p.startswith('training_data/cFos/raw/')}
gt = {Path(p).name for p in items if p.startswith('training_data/cFos/gt/')}
report = dict(commit=COMMIT, raw_count=len(raw), gt_count=len(gt),
              raw_without_gt=sorted(raw-gt), split_status='UNRESOLVED: quarantine; no tuning or evaluation', patches=[])
for name in ['patchvolume_1008_0.nii.gz', 'patchvolume_1147_0.nii.gz']:
    arrays=[]; entry={'name':name, 'files':{}}
    for kind in ('raw','gt'):
        rel=f'training_data/cFos/{kind}/{name}'
        url=f'https://raw.githubusercontent.com/erturklab/delivr_cfos/{COMMIT}/{rel}'
        dst=ROOT/kind/name; dst.parent.mkdir(exist_ok=True)
        data=dst.read_bytes() if dst.exists() else urllib.request.urlopen(url,timeout=45).read()
        assert len(data)==items[rel]['size']
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==items[rel]['sha']
        if not dst.exists(): dst.write_bytes(data)
        img=nib.load(dst); a=np.asarray(img.dataobj); arrays.append(a)
        entry['files'][kind]=dict(url=url, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
          shape=list(a.shape), dtype=str(a.dtype), zooms=list(map(float,img.header.get_zooms())),
          units=img.header.get_xyzt_units(),affine=img.affine.tolist(),axcodes=nib.aff2axcodes(img.affine),
          qform_code=int(img.header['qform_code']),sform_code=int(img.header['sform_code']))
    a,g=arrays
    entry['same_shape']=a.shape==g.shape
    entry['same_affine']=entry['files']['raw']['affine']==entry['files']['gt']['affine']
    entry['label_values']=np.unique(g).tolist()
    entry['positive_components_by_connectivity']={str(k):int(ndimage.label(g>0,ndimage.generate_binary_structure(3,k))[1]) for k in (1,2,3)}
    entry['continuity_by_array_axis']={}
    for axis in range(3):
        planes=np.moveaxis(a,axis,0)
        entry['continuity_by_array_axis'][str(axis)]=dict(
            medians=[float(np.median(p)) for p in planes],
            adjacent_correlations=[float(np.corrcoef(p.ravel(),q.ravel())[0,1]) for p,q in zip(planes[:-1],planes[1:])],
            identical_neighbors=[i for i in range(len(planes)-1) if np.array_equal(planes[i],planes[i+1])])
    report['patches'].append(entry)
(ROOT/'audit.json').write_text(json.dumps(report,indent=2))
for p in report['patches']:
    print(p['name'],p['files']['raw'], 'labels',p['label_values'][:30], 'unique',len(p['label_values']), 'components',p['positive_components_by_connectivity'])
print('inventory',len(raw),len(gt),'missing',sorted(raw-gt))
