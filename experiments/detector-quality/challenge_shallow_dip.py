"""Frozen six-percent rule: fresh demo windows plus adversarial seed-stage tests."""
import test_shallow_dip as t
b=t.b; np=t.np
from skimage.segmentation import watershed
out=b.ROOT/'test-data'/('dip-challenge-'+b.run_stamp)

def adversarial():
    cases=[]
    for name,shape,p,q,bridge,peaks,expected in [
        ('long_bright_bridge_two_objects',(31,9,1),(3,4,0),(27,4,0),288,(304,304),2),
        ('unequal_touching_shallow_saddle',(31,9,1),(3,4,0),(27,4,0),232,(400,240),2),
        ('unequal_touching_deep_saddle',(31,9,1),(3,4,0),(27,4,0),190,(400,240),2),
        ('single_object_deeper_texture',(31,9,1),(3,4,0),(12,4,0),280,(304,304),1),
        ('two_objects_3d_bright_axial_bridge',(9,9,31),(4,4,3),(4,4,27),288,(304,304),2),
    ]:
        a=np.zeros(shape,dtype=np.uint16)
        direction=int(np.argmax(np.abs(np.array(q)-p)))
        for i in range(p[direction],q[direction]+1):
            coord=list(p); coord[direction]=i; a[tuple(coord)]=bridge
        a[p]=peaks[0]; a[q]=peaks[1]
        seeds=np.array([p,q]); kept,changes=t.merge(a,seeds,.06)
        cases.append(dict(name=name,expected_objects=expected,remaining_seeds=len(kept),
                          matches_constructed_label=len(kept)==expected,changes=changes,
                          note='Constructed labels; supplied seeds isolate merge stage, not biological ground truth'))
    return cases

def run():
    out.mkdir()
    source=b.ROOT/'test-data/neatmap/RawImage_example/RawImage_merged_26.tif'
    data=b.tifffile.imread(source)[5,0]
    report={'fraction':.06,'threshold':168,'source':str(source),'frame':5,'channel':0,
            'source_sha256':b.hashlib.sha256(source.read_bytes()).hexdigest(),
            'selection':'Six predefined 256x256 windows in image 26, x=256/800/1400, y=200/450; no cutoff tuning',
            'limitations':['Fresh to this rule evaluation, not independent specimen validation','Unlabelled real examples cannot establish accuracy','All merge events retained; no biological labels inferred from totals'],
            'synthetic':adversarial(),'crops':[],'events':[]}
    display=[]
    for y in [200,450]:
        for x in [256,800,1400]:
            name=f'x{x}_y{y}'; raw=np.asfortranarray(data[y:y+256,x:x+256].T[:,:,None])
            assert raw.shape==(256,256,1)
            corr=b.Cells.remove_background(raw,shape=(21,21),form='Disk')
            seeds=np.argwhere(b.collapse_plateaus(corr,b.md.find_maxima(corr,shape=(11,11,1),threshold=168)))
            kept,changes=t.merge(corr,seeds,.06)
            again,_=t.merge(corr,seeds,.06); assert np.array_equal(kept,again)
            shapes=[]; counts=[]
            for variant,pts in [('before',seeds),('after',kept)]:
                s=watershed(-corr,t.e.markers(raw.shape,pts),mask=corr>168); shapes.append(s)
                sizes=np.bincount(s.ravel(),minlength=len(pts)+1)[1:]
                df=b.pd.DataFrame(pts,columns=['x','y','z']); df['size']=sizes; df['accepted']=df['size'].between(5,500)
                df.to_csv(out/f'{name}_{variant}.csv',index=False); counts.append(int(df.accepted.sum()))
                np.save(out/f'{name}_{variant}_shapes.npy',s)
            report['crops'].append(dict(name=name,seeds_before=len(seeds),seeds_after=len(kept),accepted_before=counts[0],accepted_after=counts[1],repeatable_seeds=True))
            for change in changes:
                p=np.array(change['removed']); q=np.array(change['retained'])
                event=dict(case=len(report['events'])+1,crop=name,**change,distance_pixels=float(np.linalg.norm(p-q)),
                           original_removed=[int(p[0]+x),int(p[1]+y)],original_retained=[int(q[0]+x),int(q[1]+y)])
                report['events'].append(event); display.append((raw,corr,seeds,kept,shapes,event))
    # Show every merge, paginated to keep individual panels readable.
    for page in range((len(display)+3)//4):
        entries=display[page*4:(page+1)*4]
        fig,axes=b.plt.subplots(len(entries),3,figsize=(10,3.3*len(entries)),squeeze=False,constrained_layout=True)
        for row,(raw,corr,seeds,kept,shapes,event) in enumerate(entries):
            p=np.array(event['removed']); q=np.array(event['retained']); center=(p+q)//2
            radius=max(10,int(np.max(np.abs(p-q)))//2+5)
            x1=max(0,int(center[0])-radius); x2=min(256,int(center[0])+radius+1)
            y1=max(0,int(center[1])-radius); y2=min(256,int(center[1])+radius+1)
            sl=(slice(x1,x2),slice(y1,y2),0); ext=[x1-.5,x2-.5,y2-.5,y1-.5]
            lo,hi=np.percentile(raw,[1,99.8])
            for col in range(3):
                ax=axes[row,col]; ax.imshow(raw[sl].T,cmap='gray',vmin=lo,vmax=hi,extent=ext,interpolation='nearest')
                ax.set_title(f"Case {event['case']} / "+['raw','before','6% rule'][col])
                if col:
                    labels=shapes[col-1][sl].T; rgba=np.zeros(labels.shape+(4,))
                    for lab in np.unique(labels):
                        if lab: rgba[labels==lab]=b.plt.get_cmap('tab20')(int(lab)%20); rgba[labels==lab,3]=.35
                    ax.imshow(rgba,extent=ext,interpolation='nearest')
                ax.scatter(q[0],q[1],marker='+',color='lime',s=70)
                ax.scatter(p[0],p[1],marker='x',color='cyan',s=45)
        fig.suptitle('Fresh image 26: green + retained seed; cyan x removed seed. Every merge shown.')
        fig.savefig(out/f'merges-page{page+1}.png',dpi=150); b.plt.close(fig)
    (out/'report.json').write_text(b.json.dumps(report,indent=2))
    print(out); print(b.json.dumps(report,indent=2))

if __name__=='__main__': run()
