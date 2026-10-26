"""Diagnostic exact-plateau geodesic reassignment; ambiguous ties remain zero."""
from collections import deque
import time
import validate_component_segmentation as v
b=v.b; np=v.np
OUT=b.ROOT/'test-data'/('review2-geodesic-'+b.run_stamp)

def geodesic(image,markers,mask):
    result=v.segment(image,markers,mask)
    components,_=b.ndi.label(mask)
    ambiguity=np.zeros(mask.shape,bool)
    for cid,sl in enumerate(b.ndi.find_objects(components),1):
        if sl is None: continue
        local=components[sl]==cid; m=np.where(local,markers[sl],0)
        ids=np.unique(m[m>0])
        if len(ids)<2: continue
        # Distances use unit face-neighbor steps inside the foreground mask.
        distances=[]
        for lab in ids:
            dist=np.full(local.shape,1e9); queue=deque()
            for p in np.argwhere(m==lab): dist[tuple(p)]=0; queue.append(tuple(p))
            while queue:
                p=queue.popleft()
                for axis in range(local.ndim):
                    for sign in [-1,1]:
                        q=list(p); q[axis]+=sign; q=tuple(q)
                        if all(0<=q[d]<local.shape[d] for d in range(local.ndim)) and local[q] and dist[q]>dist[p]+1:
                            dist[q]=dist[p]+1; queue.append(q)
            distances.append(dist)
        ds=np.stack(distances); minimum=ds.min(axis=0)
        nearest=ids[ds.argmin(axis=0)]; tied=(ds==minimum).sum(axis=0)>1
        # Reassign entire equal-value connected plateaus competing between labels.
        # Selection still depends on the original watershed: invariance is tested,
        # not assumed. This is NOT a full replacement watershed algorithm.
        baseline=result[sl].copy(); region=result[sl]; uncertain=ambiguity[sl]
        for value in np.unique(image[sl][local]):
            plateaus,n=b.ndi.label(local&(image[sl]==value))
            for pid in range(1,n+1):
                plateau=plateaus==pid
                if len(np.unique(baseline[plateau]))<2: continue
                editable=plateau&(m==0)
                region[editable]=nearest[editable]
                region[editable&tied]=0; uncertain[editable&tied]=True
    return result,ambiguity

def transforms(a):
    yield 'transpose',np.swapaxes(a,0,1),lambda x:np.swapaxes(x,0,1)
    for axis in range(a.ndim):
        yield f'flip{axis}',np.flip(a,axis),lambda x,axis=axis:np.flip(x,axis)

def check(name,image,m,mask):
    baseline=v.segment(image,m,mask); revised,amb=geodesic(image,m,mask)
    rows=[]
    for (tag,im,undo),(_,mk,_),(_,ms,_) in zip(transforms(image),transforms(m),transforms(mask)):
        plain=undo(v.segment(im,mk,ms)); geo,uncertain=geodesic(im,mk,ms)
        rows.append(dict(transform=tag,baseline_changed=int(np.count_nonzero(plain!=baseline)),
                         geodesic_changed=int(np.count_nonzero(undo(geo)!=revised)),
                         ambiguity_changed=int(np.count_nonzero(undo(uncertain)!=amb))))
    return dict(name=name,ambiguous_pixels=int(amb.sum()),reassigned_pixels=int(np.count_nonzero(revised!=baseline)),transforms=rows)

def run():
    OUT.mkdir(); report={'definition':'Equal-intensity competing plateau reassignment by unweighted face-connected mask distance; equal-distance winners explicitly ambiguous, not resolved by label ID. Experimental, not adopted.', 'tests':[],'shortcut_benchmarks':[]}
    for shape in [(9,13),(7,9,11)]:
        mask=np.ones(shape,bool); image=np.zeros(shape); m=np.zeros(shape,np.int32)
        p=tuple(1 for _ in shape); q=tuple(n-2 for n in shape); m[p]=1; m[q]=2
        report['tests'].append(check(str(len(shape))+'D_flat',image,m,mask))
    for number in [25,26]:
        data=b.tifffile.imread(b.ROOT/f'test-data/neatmap/RawImage_example/RawImage_merged_{number}.tif')[5,0]
        windows=[(800,200),(1400,200)] if number==25 else [(x,y) for y in [200,450] for x in [256,800,1400]]
        for x,y in windows:
            name=f'{number}_{x}_{y}'; raw=np.asfortranarray(data[y:y+256,x:x+256].T[:,:,None])
            corr=b.Cells.remove_background(raw,shape=(21,21),form='Disk'); mask=corr>168
            seeds=np.argwhere(b.collapse_plateaus(corr,b.md.find_maxima(corr,shape=(11,11,1),threshold=168)))
            m=v.e.markers(raw.shape,seeds); image=-corr.astype(float)
            times={}
            for label,fn in [('reference',v.segment_reference),('shortcut',v.segment)]:
                samples=[]
                for _ in range(3):
                    start=time.perf_counter(); a=fn(image,m,mask); samples.append(time.perf_counter()-start)
                times[label]=float(np.median(samples))
            assert np.array_equal(v.segment_reference(image,m,mask),v.segment(image,m,mask))
            report['shortcut_benchmarks'].append(dict(crop=name,median_seconds_per_crop=times))
            report['tests'].append(check(name,image,m,mask))
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2))
    print(OUT)
    print(b.json.dumps(report,indent=2))

if __name__=='__main__': run()
