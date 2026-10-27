"""Create a blinded, local manual 3D object-review pilot; no auto labels."""
from pathlib import Path
import json,hashlib,base64,io
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'test-data/reference-review-v1'

def run():
    OUT.mkdir(exist_ok=False)
    source=ROOT/'test-data/public-cellfinder-3d/ch0_zyx.npy'
    a=np.load(source,mmap_mode='r')
    # Fixed disjoint grid windows, chosen without consulting detections.
    locations=[(96,96),(288,96),(480,96),(96,320),(288,320),(480,320)]
    regions=[]; images={}
    for i,(x,y) in enumerate(locations):
        crop=a[:,y:y+64,x:x+64]
        low,high=map(float,np.percentile(crop,[1,99.8]))
        assert high>low
        rid=f'R{i+1}'; frames=[]
        for plane in crop:
            displayed=np.uint8(np.clip((plane.astype(float)-low)/(high-low),0,1)*255)
            buf=io.BytesIO(); Image.fromarray(displayed).save(buf,format='PNG')
            frames.append('data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode())
        images[rid]=frames
        regions.append(dict(id=rid,origin_xyz=[x,y,0],shape_zyx=list(crop.shape),
                            split='tuning' if i in [0,2,4] else 'held_out',display_range=[low,high]))
    manifest=dict(review_id='public-cellfinder-reference-v1',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        voxel_xyz_um=[2,2,5],regions=regions,selection='Six predefined disjoint grid windows, no detection-based selection',
        label_definition='Provisional distinct fluorescent object judged in 3D, not verified cell identity; stain not confirmed',
        statuses=['object','uncertain','artifact','edge'],heldout_policy='Keep held_out labels out of parameter selection; these are same-specimen windows, not independent brains')
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    template=Path(__file__).with_name('reference_review_template.html').read_text()
    (OUT/'review.html').write_text(template.replace('__MANIFEST__',json.dumps(manifest)).replace('__IMAGES__',json.dumps(images)))
    print(OUT/'review.html')

if __name__=='__main__': run()
