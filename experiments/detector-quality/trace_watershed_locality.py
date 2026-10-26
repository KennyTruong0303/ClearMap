"""Isolate nonlocal watershed changes after removing unrelated markers."""
import inspect
import test_shallow_dip as t
from skimage.segmentation import watershed
import skimage
from validate_component_segmentation import segment as component_segment
b=t.b; np=b.np
root=b.ROOT/'test-data/dip-challenge-20261026T072421541529Z'
out=b.ROOT/'test-data'/('watershed-locality-'+b.run_stamp); out.mkdir()
data=b.tifffile.imread(b.ROOT/'test-data/neatmap/RawImage_example/RawImage_merged_26.tif')[5,0]
report={'skimage':skimage.__version__,'watershed_source':inspect.getfile(watershed),'crops':[]}

def component_watershed(image,markers,labels):
    return component_segment(image,markers,labels>0)

for x,y,targets in [(1400,200,[(246,44),(246,46),(247,45)]),(1400,450,[(194,5)])]:
    name=f'x{x}_y{y}'; raw=np.asfortranarray(data[y:y+256,x:x+256].T[:,:,None])
    corr=b.Cells.remove_background(raw,shape=(21,21),form='Disk'); mask=corr>168
    labels,n=b.ndi.label(mask)
    table=b.pd.read_csv(root/f'{name}_before.csv'); seeds=table[['x','y','z']].to_numpy()
    kept=set(map(tuple,b.pd.read_csv(root/f'{name}_after.csv')[['x','y','z']].to_numpy()))
    old=t.e.markers(corr.shape,seeds); new=old.copy(); removed=[]
    for p in seeds:
        if tuple(p) not in kept:
            new[tuple(p)]=0; removed.append(dict(point=p.tolist(),component=int(labels[tuple(p)])))
    a=watershed(-corr,old,mask=mask); c=watershed(-corr,new,mask=mask)
    assert np.array_equal(np.bincount(a.ravel(),minlength=len(seeds)+1)[1:],table['size'].to_numpy())
    ca=component_watershed(-corr,old,labels); cc=component_watershed(-corr,new,labels)
    changed=np.unique(labels[a!=c]); removed_components={p['component'] for p in removed}
    unrelated=[int(l) for l in changed if l not in removed_components]
    rows=[]
    for px,py in targets:
        lab=int(labels[px,py,0]); seedid=int(old[px,py,0]); component=labels==lab
        only=np.where(component,old,0)
        isolated=watershed(-corr,only,mask=component)
        # Identical local inputs, with only unrelated markers removed elsewhere.
        assert np.array_equal(old[component],new[component])
        rows.append(dict(point=[px,py],component=lab,component_pixels=int(component.sum()),
            old_size=int((a==seedid).sum()),new_size=int((c==seedid).sum()),
            componentwise_old_size=int((ca==seedid).sum()),componentwise_new_size=int((cc==seedid).sum()),
            isolated_size=int((isolated==seedid).sum()),local_inputs_identical=True))
    # Signed negation excludes unsigned wraparound as the explanation.
    sa=watershed(-corr.astype(np.float64),old,mask=mask)
    sc=watershed(-corr.astype(np.float64),new,mask=mask)
    # Diagnostic only: unique sub-intensity pixel priorities remove exact ties.
    priority=-corr.astype(np.float64)+np.arange(corr.size).reshape(corr.shape)*1e-7
    ua=watershed(priority,old,mask=mask); uc=watershed(priority,new,mask=mask)
    report['crops'].append(dict(crop=name,removed=removed,unrelated_changed_components=unrelated,targets=rows,
        signed_matches_unsigned_before=bool(np.array_equal(sa,a)),signed_matches_unsigned_after=bool(np.array_equal(sc,c)),
        unique_priority_unrelated_changed_pixels=int(np.count_nonzero((ua!=uc)&~np.isin(labels,list(removed_components)))),
        componentwise_unrelated_changed_pixels=int(np.count_nonzero((ca!=cc)&~np.isin(labels,list(removed_components))))))
    for tag,arr in [('before',a),('after',c),('component_before',ca),('component_after',cc)]: np.save(out/f'{name}_{tag}.npy',arr)

# Two disconnected foreground islands: deleting a seed in island A must not
# alter competing seeds in island B. Sweep seed placements on a flat plateau.
failures=[]
for count in range(1,10):
    image=np.zeros((15,25),dtype=float); mask=np.zeros_like(image,dtype=bool)
    mask[1:4,1:12]=True; mask[7:14,15:24]=True
    markers=np.zeros(image.shape,dtype=np.int32)
    for i in range(count): markers[2,i+2]=i+1
    markers[9,17]=20; markers[11,21]=21
    revised=markers.copy(); revised[2,2]=0
    a=watershed(image,markers,mask=mask); c=watershed(image,revised,mask=mask)
    changed=int(np.count_nonzero(a[7:14,15:24]!=c[7:14,15:24]))
    if changed: failures.append(dict(unrelated_seed_count=count,changed_pixels=changed))
    if count==1:
        labels,_=b.ndi.label(mask)
        ca=component_watershed(image,markers,labels); cc=component_watershed(image,revised,labels)
        assert np.array_equal(ca[7:14,15:24],cc[7:14,15:24])
        fig,axes=b.plt.subplots(2,2,figsize=(8,6),constrained_layout=True)
        for ax,arr,title in zip(axes.ravel(),[a,c,ca,cc],['Global: before','Global: unrelated seed removed','Per component: before','Per component: unrelated seed removed']):
            ax.imshow(arr[7:14,15:24],vmin=19,vmax=22,cmap='viridis',interpolation='nearest'); ax.set_title(title,fontsize=10)
        fig.suptitle('Unchanged island with two seeds: global watershed changes 7 pixels\nPer-component watershed preserves it. Synthetic flat signal; no biology implied.')
        fig.savefig(out/'synthetic-locality.png',dpi=140)
report['synthetic_disconnected_plateau_failures']=failures
(out/'report.json').write_text(b.json.dumps(report,indent=2))
print(out); print(b.json.dumps(report,indent=2))
