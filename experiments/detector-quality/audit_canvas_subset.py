"""Inspect a three-plane CANVAS training subset without running a detector."""
from pathlib import Path
import csv,json,hashlib
import numpy as np
import tifffile
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent/'test-data/canvas-audit'
rows=list(csv.DictReader((root/'region2.csv').open()))
xyz=np.array([[int(r[k]) for k in ('x','y','z')] for r in rows])
report={'split':'official TRAIN region2; QA only','label_count':len(rows),
        'unique_ids':len({r['id'] for r in rows}),
        'unique_coordinates':len(np.unique(xyz,axis=0)),
        'coordinate_min':xyz.min(axis=0).tolist(),'coordinate_max':xyz.max(axis=0).tolist(),
        'all_in_published_roi':bool(np.all((xyz>=[4402,3198,1132])&(xyz<[4702,3498,1282]))),
        'planes':[],'spacing_status':'paper XYZ 1.8/1.8/4 um; verify TIFF metadata',
        'alignment_hypothesis':'CSV global x/y and filename prefix z, zero-based; visual audit required'}
crops=[]
for path in sorted(root.glob('*.tif')):
    z=int(path.name.split('_')[0])
    with tifffile.TiffFile(path) as tf:
        a=tf.asarray();p=tf.pages[0]
        report['planes'].append(dict(file=path.name,z=z,shape=list(a.shape),dtype=str(a.dtype),
          bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
          axes=tf.series[0].axes,tags={k:str(p.tags[k].value) for k in ('ImageDescription','XResolution','YResolution','ResolutionUnit') if k in p.tags}))
        crops.append(a[3198:3498,4402:4702].copy())
assert len(crops)==3
v=np.stack(crops);np.save(root/'training-region2-three-planes-zyx.npy',v)
report['medians']=[float(np.median(p)) for p in v]
report['adjacent_correlations']=[float(np.corrcoef(v[i].ravel(),v[i+1].ravel())[0,1]) for i in (0,1)]
lo,hi=np.percentile(v,[1,99.8]);canvas=Image.new('RGB',(930,350),'#202020');d=ImageDraw.Draw(canvas)
for i,(p,meta) in enumerate(zip(v,report['planes'])):
    im=Image.fromarray(np.uint8(np.clip((p-lo)/(hi-lo),0,1)*255)).convert('RGB');q=ImageDraw.Draw(im)
    for x,y,z in xyz[xyz[:,2]==meta['z']]:
        x-=4402;y-=3198;q.ellipse((x-4,y-4,x+4,y+4),outline='cyan')
    canvas.paste(im,(i*310,25));d.text((i*310+5,5),f"prefix {meta['z']} | exact-Z CSV centers",fill='white')
canvas.save(root/'alignment-qc.png');(root/'audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
