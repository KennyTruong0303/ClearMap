"""Validate experimental per-component watershed without shallow-dip merging."""
import time
import test_direct_markers as e
from skimage.segmentation import watershed
b=e.base; np=b.np
OUT=b.ROOT/'test-data'/('component-validation-'+b.run_stamp)

def segment_reference(image,markers,mask):
    labels,_=b.ndi.label(mask)
    result=np.zeros(markers.shape,dtype=np.int32)
    for lab,sl in enumerate(b.ndi.find_objects(labels),1):
        if sl is None: continue
        local=labels[sl]==lab
        local_markers=np.where(local,markers[sl],0)
        if not np.any(local_markers): continue
        result[sl]+=watershed(image[sl],local_markers,mask=local)
    return result

def segment(image,markers,mask):
    """Equivalent shortcut: flood single-marker components without watershed."""
    labels,_=b.ndi.label(mask)
    result=np.zeros(markers.shape,dtype=np.int32)
    for lab,sl in enumerate(b.ndi.find_objects(labels),1):
        if sl is None: continue
        local=labels[sl]==lab
        local_markers=np.where(local,markers[sl],0)
        ids=np.unique(local_markers[local_markers>0])
        if not len(ids): continue
        if len(ids)==1:
            result[sl][local]=ids[0]
        else:
            result[sl]+=watershed(image[sl],local_markers,mask=local)
    return result

def invariants(image,m,mask):
    a=segment(image,m,mask)
    assert np.array_equal(a,segment_reference(image,m,mask))
    assert not np.any(a[~mask])
    assert np.array_equal(a[m>0],m[m>0])
    assert set(np.unique(a))<=set(np.unique(m))
    labels,_=b.ndi.label(mask)
    for lab in np.unique(labels):
        if not lab: continue
        local=labels==lab; allowed=set(np.unique(m[local]))
        assert set(np.unique(a[local]))<=allowed|{0}
        if any(allowed): assert np.all(a[local]>0)
    assert np.array_equal(a,segment(image,m,mask))
    # Delete a seed and verify every disconnected component is unchanged.
    coords=np.argwhere(m>0)
    if len(coords):
        p=tuple(coords[0]); changed=m.copy(); changed[p]=0
        c=segment(image,changed,mask); unrelated=labels!=labels[p]
        assert np.array_equal(a[unrelated],c[unrelated])
    return a

def synthetic():
    tests=[]; rng=np.random.default_rng(20261026)
    for ndim,shape in [(2,(21,25)),(3,(13,15,17))]:
        for case in range(12):
            mask=rng.random(shape)>.48
            image=rng.integers(0,5,size=shape).astype(float)
            coords=np.argwhere(mask); m=np.zeros(shape,dtype=np.int32)
            for i,p in enumerate(coords[::max(1,len(coords)//25)]): m[tuple(p)]=i+1
            a=invariants(image,m,mask)
            # Padding and memory layout must not alter spatial labels.
            pad=[(2,3)]*ndim; sl=tuple(slice(2,2+n) for n in shape)
            assert np.array_equal(a,segment(np.pad(image,pad),np.pad(m,pad),np.pad(mask,pad))[sl])
            assert np.array_equal(a,segment(np.asfortranarray(image),np.asfortranarray(m),np.asfortranarray(mask)))
            tests.append(f'{ndim}D_random_tied_case_{case}')
    for name,mask,m in [('empty',np.zeros((5,5),bool),np.zeros((5,5),np.int32)),
                        ('unseeded',np.ones((5,5),bool),np.zeros((5,5),np.int32))]:
        assert not segment(np.zeros((5,5)),m,mask).any(); tests.append(name)
    mask=np.eye(5,dtype=bool); m=np.zeros((5,5),np.int32); m[0,0]=1
    assert np.count_nonzero(segment(np.zeros((5,5)),m,mask))==1
    tests.append('diagonal_contacts_separate_under_face_connectivity')
    return tests

def run():
    OUT.mkdir(); report={'merge_rule_enabled':False,'synthetic_passed':synthetic(),'crops':[],
        'scope':'Stage-level evaluation on eight demo crops; synthetic 3D is not real 3D biological validation'}
    plotted=[]
    for number in [25,26]:
        source=b.ROOT/f'test-data/neatmap/RawImage_example/RawImage_merged_{number}.tif'
        image=b.tifffile.imread(source)[5,0]
        windows=[(800,200),(1400,200)] if number==25 else [(x,y) for y in [200,450] for x in [256,800,1400]]
        for x,y in windows:
            name=f'image{number}_x{x}_y{y}'
            raw=np.asfortranarray(image[y:y+256,x:x+256].T[:,:,None])
            corr=b.Cells.remove_background(raw,shape=(21,21),form='Disk'); mask=corr>168
            seeds=np.argwhere(b.collapse_plateaus(corr,b.md.find_maxima(corr,shape=(11,11,1),threshold=168)))
            m=e.markers(raw.shape,seeds); priority=-corr.astype(float)
            a=invariants(priority,m,mask)
            old=watershed(priority,m,mask=mask)
            timings={}
            for variant,fn in [('global',lambda:watershed(priority,m,mask=mask)),('component',lambda:segment(priority,m,mask))]:
                times=[]
                for _ in range(3):
                    start=time.perf_counter(); result=fn(); times.append(time.perf_counter()-start)
                    assert np.array_equal(result,old if variant=='global' else a)
                timings[variant]=float(np.median(times))
            n=len(seeds)+1; sa=np.bincount(old.ravel(),minlength=n)[1:]; sb=np.bincount(a.ravel(),minlength=n)[1:]
            accepted_a=(sa>=5)&(sa<=500); accepted_b=(sb>=5)&(sb<=500)
            df=b.pd.DataFrame(seeds,columns=['x','y','z']); df['global_size']=sa; df['component_size']=sb
            df['global_accepted']=accepted_a; df['component_accepted']=accepted_b
            df.to_csv(OUT/(name+'.csv'),index=False)
            changes=df[accepted_a!=accepted_b].to_dict(orient='records')
            report['crops'].append(dict(name=name,seeds=len(seeds),global_accepted=int(accepted_a.sum()),component_accepted=int(accepted_b.sum()),
                changed_pixels=int(np.count_nonzero(a!=old)),changed_sizes=int(np.count_nonzero(sa!=sb)),acceptance_changes=changes,median_seconds=timings))
            np.save(OUT/(name+'_global.npy'),old); np.save(OUT/(name+'_component.npy'),a)
            if changes: plotted.append((name,raw,old,a,changes))
    if plotted:
        fig,axes=b.plt.subplots(len(plotted),3,figsize=(10,3*len(plotted)),squeeze=False,constrained_layout=True)
        for row,(name,raw,old,a,changes) in enumerate(plotted):
            p=changes[0]; x,y=int(p['x']),int(p['y']); r=9
            x1,x2=max(0,x-r),min(256,x+r+1); y1,y2=max(0,y-r),min(256,y+r+1)
            sl=(slice(x1,x2),slice(y1,y2),0); ext=[x1-.5,x2-.5,y2-.5,y1-.5]; lo,hi=np.percentile(raw,[1,99.8])
            for col,labels in enumerate([None,old,a]):
                ax=axes[row,col]; ax.imshow(raw[sl].T,cmap='gray',vmin=lo,vmax=hi,extent=ext,interpolation='nearest')
                if labels is not None:
                    patch=labels[sl].T; rgba=np.zeros(patch.shape+(4,))
                    for lab in np.unique(patch):
                        if lab: rgba[patch==lab]=b.plt.get_cmap('tab20')(int(lab)%20); rgba[patch==lab,3]=.4
                    ax.imshow(rgba,extent=ext,interpolation='nearest')
                ax.scatter(x,y,marker='+',color='lime'); ax.set_title(['Raw','Global watershed','Per component'][col])
                if col==0: ax.set_ylabel(name)
        fig.suptitle('First acceptance-change location per affected crop; all changes are in CSV/report')
        fig.savefig(OUT/'boundary-review.png',dpi=150)
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2))
    print(OUT); print(b.json.dumps(report,indent=2))

if __name__=='__main__': run()
