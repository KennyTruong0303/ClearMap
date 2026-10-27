"""Fetch pinned official BrainGlobe cellfinder sample, preserving provenance."""
from pathlib import Path
import urllib.request,json,hashlib,concurrent.futures,time
import numpy as np
import tifffile
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'test-data/public-cellfinder-3d'
COMMIT='105f5942d1b9cac98d7a2d5ee591f9826eea5ab0'
PREFIX='tests/data/integration/detection/crop_planes/'

def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ClearMap-local-validation'}),timeout=30) as r: return r.read()
        except Exception:
            if attempt==2: raise
            time.sleep(1)

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    tree=json.loads(get(f'https://api.github.com/repos/brainglobe/cellfinder/git/trees/{COMMIT}?recursive=1'))
    files=[x for x in tree['tree'] if x['path'].startswith(PREFIX) and x['path'].endswith('.tif')]
    files=[x for x in files if int(Path(x['path']).stem[-4:])<30]
    assert len(files)==60,(len(files),'Expected paired 30-plane sample')
    assert sum(x['size'] for x in files)<150_000_000
    def fetch(item):
        rel=Path(item['path']).relative_to(PREFIX); path=OUT/rel; path.parent.mkdir(exist_ok=True)
        url=f'https://raw.githubusercontent.com/brainglobe/cellfinder/{COMMIT}/{item["path"]}'
        data=path.read_bytes() if path.exists() else get(url)
        assert len(data)==item['size']
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==item['sha']
        if not path.exists(): path.write_bytes(data)
        return dict(path=str(rel),url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),git_blob=item['sha'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: verified=list(pool.map(fetch,files))
    shapes={}
    for ch in [0,1]:
        stack=np.stack([tifffile.imread(OUT/f'ch{ch}/ch{ch}{i:04}.tif') for i in range(30)])
        np.save(OUT/f'ch{ch}_zyx.npy',stack); shapes[str(ch)]=dict(shape=list(stack.shape),dtype=str(stack.dtype),min=int(stack.min()),max=int(stack.max()))
    report=dict(commit=COMMIT,source='https://brainglobe.info/tutorials/cellfinder-detection.html',
        axes='ZYX',voxel_size_xyz_um=[2,2,5],channel_roles={'0':'Signal','1':'Background'},
        limitations=['Official tutorial notes artifacts and imperfect detection','Not independent cell labels or iDISCO accuracy validation','Modality and stain not independently established for this particular crop'],
        arrays=shapes,files=verified,total_bytes=sum(x['bytes'] for x in verified))
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)); print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))

if __name__=='__main__': run()
