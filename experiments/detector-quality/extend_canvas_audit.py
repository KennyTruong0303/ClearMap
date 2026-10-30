"""Bounded TRAIN-only continuity and coordinate audit, no detection/tuning."""
from pathlib import Path
import urllib.request, re, json, csv, hashlib, concurrent.futures
import numpy as np
import tifffile
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent/'test-data/canvas-audit'
BASE='https://images.lightsheetdata.com/388u1ei0otxmjkwpebn4/CANVAS-2025/cFos_brain_8/image/'
listing=(ROOT/'image-index.html').read_text(encoding='utf-8-sig')
names=re.findall(r'href="([^"]+\.tif)"',listing)
selected=sorted(n for n in names if 1130<=int(n.split('_')[0])<=1141)
assert len(selected)==12
(ROOT/'expanded-source-list.json').write_text(json.dumps(selected,indent=2))
def fetch(name):
    path=ROOT/name
    if not path.exists():
        tmp=path.with_suffix('.part')
        with urllib.request.urlopen(BASE+name,timeout=90) as response, tmp.open('wb') as f:
            expected=int(response.headers['Content-Length'])
            while True:
                block=response.read(1024*1024)
                if not block:break
                f.write(block)
        assert tmp.stat().st_size==expected
        tmp.rename(path)
    with tifffile.TiffFile(path) as tf:
        a=tf.asarray()
        assert a.shape==(10258,5599) and a.dtype==np.uint16
        crop=a[3178:3518,4382:4722].copy()
    record=dict(file=name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    print('Verified',name,flush=True)
    return crop,record
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: result=list(pool.map(fetch,selected))
v=np.stack([r[0] for r in result]); np.save(ROOT/'expanded-zyx.npy',v)
rows=list(csv.DictReader((ROOT/'region2.csv').open()))
xyz=np.array([[int(r[k]) for k in ('x','y','z')] for r in rows])
outside=np.any((xyz<[4402,3198,1132])|(xyz>=[4702,3498,1282]),axis=1)
report=dict(files=[r[1] for r in result],origin_xyz=[4382,3178,1130],shape_zyx=list(v.shape),
  medians=[float(np.median(p)) for p in v],
  correlations=[float(np.corrcoef(p.ravel(),q.ravel())[0,1]) for p,q in zip(v[:-1],v[1:])],
  outside_nominal_half_open_count=int(outside.sum()),
  outside_by_axis=[int(((xyz[:,i]<lo)|(xyz[:,i]>=hi)).sum()) for i,lo,hi in [(0,4402,4702),(1,3198,3498),(2,1132,1282)]],
  outside_labels=[rows[i] for i in np.flatnonzero(outside)],
  spacing_source='paper XYZ1.8/1.8/4um; TIFF not calibrated',shift_diagnostics=[])
# Descriptive alignment diagnostic only: not a correction rule or threshold selection.
pts=xyz[(xyz[:,2]>=1133)&(xyz[:,2]<=1138)]
for dz in (-1,0,1):
 for dy in (-1,0,1):
  for dx in (-1,0,1):
   q=pts+[dx,dy,dz]-[4382,3178,1130]
   values=v[q[:,2],q[:,1],q[:,0]]
   report['shift_diagnostics'].append(dict(delta_xyz=[dx,dy,dz],n=len(q),median_intensity=float(np.median(values))))
lo,hi=np.percentile(v,[1,99.8]);c=Image.new('RGB',(1020,760),'#202020');d=ImageDraw.Draw(c)
for i,z in enumerate([1132,1133,1134,1135,1136,1137]):
 im=Image.fromarray(np.uint8(np.clip((v[z-1130].astype(float)-lo)/(hi-lo),0,1)*255)).convert('RGB');p=ImageDraw.Draw(im)
 for x,y,_ in xyz[xyz[:,2]==z]:
  x-=4382;y-=3178;p.ellipse((x-4,y-4,x+4,y+4),outline='cyan')
 p.rectangle((20,20,319,319),outline='orange')
 x=i%3*340;y=i//3*380;c.paste(im,(x,y+25));d.text((x+5,y+5),f'prefix {z}; cyan exact-Z centers',fill='white')
c.save(ROOT/'expanded-alignment.png');(ROOT/'expanded-audit.json').write_text(json.dumps(report,indent=2))
print('DONE',json.dumps({k:report[k] for k in ['medians','correlations','outside_by_axis']}),flush=True)
