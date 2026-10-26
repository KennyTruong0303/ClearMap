"""Experimental seed suppression by relative saddle depth; no production edits."""
import test_direct_markers as e
from skimage.segmentation import watershed
b=e.base; np=b.np
ROOT=b.ROOT/'test-data/direct-markers-20261026T030829096851Z'
OUT=b.ROOT/'test-data'/('shallow-dip-'+b.run_stamp)

def merge(image,seeds,fraction,threshold=168):
    # Strongest first; equal peaks use lexicographic coordinate order.
    order=sorted(range(len(seeds)),key=lambda i:(-float(image[tuple(seeds[i])]),tuple(seeds[i])))
    kept=[]; changes=[]
    for i in order:
        p=tuple(seeds[i]); peak=float(image[p]); floor=peak*(1-fraction)
        labels,_=b.ndi.label((image>=floor)&(image>threshold))
        component=labels[p]
        partners=[j for j in kept if component and labels[tuple(seeds[j])]==component]
        if partners:
            j=partners[0]
            changes.append(dict(removed=seeds[i].tolist(),retained=seeds[j].tolist(),peak=peak,connection_floor=floor))
        else: kept.append(i)
    return np.array(sorted([seeds[i].tolist() for i in kept]),dtype=int).reshape(-1,image.ndim),changes

def synthetic():
    results=[]
    for name,peaks,bridge,expected in [
        ('one_object_shallow_ripple',(304,304),288,1),
        ('two_deep_separated_peaks',(304,304),180,2),
        ('touching_unequal_peaks_deep_valley',(400,240),180,2),
        ('two_objects_shallow_valley_ambiguity',(400,240),232,1)]:
        a=np.zeros((9,3),dtype=float); a[1,1]=peaks[0]; a[7,1]=peaks[1]; a[2:7,1]=bridge
        seeds=np.array([[1,1],[7,1]])
        kept,_=merge(a,seeds,.06)
        assert len(kept)==expected
        results.append(dict(case=name,output_seeds=len(kept),expected_algorithm_output=expected,
             interpretation='KNOWN OVERMERGE if these are two real objects' if 'ambiguity' in name else 'expected behavior'))
    # Only retained seeds can suppress another: avoids chaining through discarded peaks.
    empty,_=merge(np.zeros((3,3)),np.empty((0,2),dtype=int),.06)
    assert empty.shape==(0,2)
    return results

def run():
    OUT.mkdir()
    report={'rule':'Keep strongest seeds; suppress a weaker/equal seed only if a face-connected path above both 168 and (1-fraction)*its peak reaches an already retained seed. Equal ties use lexicographic order.',
            'synthetic':synthetic(),'runs':[],'merges':{},'scope':'2D stage-level experiment, not validated cell counts; A/B excluded from tuning'}
    results={}
    for region in ['center','right']:
        raw=np.load(ROOT/(region+'.npy')); corr=b.Cells.remove_background(raw,shape=(21,21),form='Disk')
        mask=b.collapse_plateaus(corr,b.md.find_maxima(corr,shape=(11,11,1),threshold=168))
        seeds=np.argwhere(mask)
        for fraction in [0,.03,.05,.06,.10,.15]:
            kept,changes=merge(corr,seeds,fraction)
            shapes=watershed(-corr,e.markers(raw.shape,kept),mask=corr>168)
            for _ in range(2):
                again,_=merge(corr,seeds,fraction)
                assert np.array_equal(again,kept)
                assert np.array_equal(shapes,watershed(-corr,e.markers(raw.shape,again),mask=corr>168))
            sizes=np.bincount(shapes.ravel(),minlength=len(kept)+1)[1:]
            df=b.pd.DataFrame(kept,columns=['x','y','z']); df['size']=sizes; df['accepted']=df['size'].between(5,500)
            key=f'{region}_{fraction:.2f}'; df.to_csv(OUT/(key+'.csv'),index=False)
            np.save(OUT/(key+'_shapes.npy'),shapes)
            report['runs'].append(dict(region=region,fraction=fraction,seeds=len(kept),accepted=int(df.accepted.sum()),three_repeats_identical=True))
            report['merges'][key]=changes
            results[region,fraction]=(raw,shapes,df)
    cases=[('right',150,39,'Reviewed upper object'),('right',163,51,'Separate lower neighbor'),('right',190,170,'C'),
           ('center',113,43,'Reviewed center 1'),('center',33,138,'Reviewed center 2'),('center',98,113,'Reviewed center 3')]
    fig,axes=b.plt.subplots(3,3,figsize=(10,9),constrained_layout=True)
    report['reviewed_cases']=[]
    for row,(region,x,y,title) in enumerate(cases):
        rec={'case':title,'variants':{}}
        for fraction in [0,.06]:
            raw,shapes,df=results[region,fraction]
            local=df[df.x.between(x-8,x+8)&df.y.between(y-8,y+8)]
            rec['variants'][str(fraction)]=local.to_dict(orient='records')
        report['reviewed_cases'].append(rec)
        if row>=3: continue
        raw=results[region,0][0]; lo,hi=np.percentile(raw[:,:,0],[1,99.8])
        for col,fraction in enumerate([None,0,.06]):
            ax=axes[row,col]; sl=(slice(x-8,x+9),slice(y-8,y+9),0); ext=[x-8.5,x+8.5,y+8.5,y-8.5]
            ax.imshow(raw[sl].T,cmap='gray',vmin=lo,vmax=hi,extent=ext,interpolation='nearest')
            ax.set_title(title+' / raw' if fraction is None else ('Before' if fraction==0 else '6% dip rule'))
            if fraction is not None:
                _,shapes,df=results[region,fraction]; labels=shapes[sl].T; rgba=np.zeros(labels.shape+(4,))
                for lab in np.unique(labels):
                    if lab: rgba[labels==lab]=b.plt.get_cmap('tab20')(int(lab)%20); rgba[labels==lab,3]=.35
                ax.imshow(rgba,extent=ext,interpolation='nearest')
                for item in rec['variants'][str(fraction)]:
                    ax.scatter(item['x'],item['y'],marker='+',color='lime' if item['accepted'] else 'yellow')
                    ax.annotate(str(item['size']),(item['x'],item['y']),xytext=(5,5),textcoords='offset points',color='white')
    fig.suptitle('Shallow-dip trial: fixed detection threshold; numbers are assigned pixel counts')
    fig.savefig(OUT/'comparison.png',dpi=150)
    report['input_hashes']={r:b.hashlib.sha256((ROOT/(r+'.npy')).read_bytes()).hexdigest() for r in ['center','right']}
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2))
    print(OUT); print(b.json.dumps({k:report[k] for k in ['synthetic','runs','reviewed_cases']},indent=2))

if __name__=='__main__': run()
