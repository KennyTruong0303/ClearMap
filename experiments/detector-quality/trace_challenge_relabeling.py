"""Separate seed deletion from sequential marker-ID renumbering."""
import test_shallow_dip as t
from skimage.segmentation import watershed
b=t.b; np=b.np
root=b.ROOT/'test-data/dip-challenge-20261026T072421541529Z'
data=b.tifffile.imread(b.ROOT/'test-data/neatmap/RawImage_example/RawImage_merged_26.tif')[5,0]
report=[]
for x,y in [(1400,200),(1400,450)]:
    name=f'x{x}_y{y}'; raw=np.asfortranarray(data[y:y+256,x:x+256].T[:,:,None])
    corr=b.Cells.remove_background(raw,shape=(21,21),form='Disk')
    before=b.pd.read_csv(root/f'{name}_before.csv'); after=b.pd.read_csv(root/f'{name}_after.csv')
    seeds=before[['x','y','z']].to_numpy(); kept=set(map(tuple,after[['x','y','z']].to_numpy()))
    markers=t.e.markers(raw.shape,seeds)
    for p in seeds:
        if tuple(p) not in kept: markers[tuple(p)]=0
    shapes=watershed(-corr,markers,mask=corr>168)
    sizes=np.bincount(shapes.ravel(),minlength=len(seeds)+1)[1:]
    events=[]
    for i,item in before.iterrows():
        if tuple(seeds[i]) in kept and bool(item.accepted)!=(5<=sizes[i]<=500):
            events.append(dict(x=int(item.x),y=int(item.y),before=int(item['size']),fixed_ids_after=int(sizes[i])))
    report.append(dict(crop=name,acceptance_changes_with_original_ids=events))
(root/'fixed-id-trace.json').write_text(b.json.dumps(report,indent=2)); print(b.json.dumps(report,indent=2))
