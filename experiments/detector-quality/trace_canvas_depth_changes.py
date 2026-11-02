"""Trace seven context-sensitive seeds; no biological labels or production edits."""
import validate_component_segmentation as v
from test_canvas_context import CORE_LO, CORE_HI
b=v.b; np=b.np
ROOT=b.ROOT/'test-data'
PRIOR=ROOT/'canvas-stages-20261030T074022793575Z'
OUT=ROOT/('canvas-trace-'+b.run_stamp)

def run():
    OUT.mkdir()
    a=np.load(ROOT/'canvas-audit/depth20-zyx.npy').transpose(2,1,0)
    origin=np.array([4382,3178,1126]); runs={}
    for h in [6,8]:
        lo=CORE_LO-[40,40,h]; hi=CORE_HI+[40,40,h]
        sl=tuple(slice(int(l),int(u)) for l,u in zip(lo-origin,hi-origin))
        raw=np.asfortranarray(a[sl]); corr=b.Cells.remove_background(raw,shape=(21,21),form='Disk')
        seeds=b.Cells.ap.where(b.ORIGINAL(corr,shape=(11,11,1),threshold=168,h_max=None),processes=1).array
        markers=v.e.markers(corr.shape,seeds); mask=corr>168
        seg=v.segment(-corr,markers,mask); cc,_=b.ndi.label(mask)
        runs[h]=dict(lo=lo,sl=sl,corr=corr,seeds=seeds,seg=seg,cc=cc)
    small,large=runs[6],runs[8]
    assert np.array_equal(small['corr'],large['corr'][:,:,2:-2])
    # Counterfactual: larger support with precisely the original seed coordinates.
    old_seeds=small['seeds']+small['lo']-large['lo']
    counter=v.segment(-large['corr'],v.e.markers(a.shape,old_seeds),large['corr']>168)
    left=b.pd.read_csv(PRIOR/'run1_z6_core.csv'); right=b.pd.read_csv(PRIOR/'run2_z8_core.csv')
    joined=left.merge(right,on=['x','y','z'],suffixes=('_6','_8'))
    changed=joined[joined.direct_component_6!=joined.direct_component_8]
    assert len(changed)==7
    records=[]; traced_masks={}
    for number,row in enumerate(changed.itertuples(),1):
        point=np.array([row.x,row.y,row.z]); details={}; masks={}; ids={}
        for h,r in runs.items():
            p=point-r['lo']; idx=int(np.flatnonzero(np.all(r['seeds']==p,axis=1))[0])+1; ids[h]=idx
            component=r['cc']==r['cc'][tuple(p)]; coords=np.argwhere(component)
            seed_ids=np.flatnonzero(component[tuple(r['seeds'].T)])
            faces=[f'{ax}{side}' for ax in range(3) for side,i in [('low',0),('high',-1)] if np.take(component,i,axis=ax).any()]
            full=np.zeros(a.shape,bool); full[r['sl']]=r['seg']==idx; masks[h]=full
            details[str(h)]=dict(size=int(full.sum()),component_voxels=int(component.sum()),component_seed_count=len(seed_ids),
                component_bounds_lower=(coords.min(0)+r['lo']).tolist(),component_bounds_upper_exclusive=(coords.max(0)+r['lo']+1).tolist(),
                component_faces=faces,component_seeds_xyz=(r['seeds'][seed_ids]+r['lo']).tolist())
        assert details['6']['size']==row.direct_component_6 and details['8']['size']==row.direct_component_8
        cf=counter==ids[6]
        shared=np.zeros(a.shape,bool); shared[small['sl']]=True
        record=dict(object=number,seed_xyz=point.tolist(),contexts=details,
            gained_voxels=int((masks[8]&~masks[6]).sum()),lost_voxels=int((masks[6]&~masks[8]).sum()),
            changes_in_shared_volume=int(((masks[6]!=masks[8])&shared).sum()),
            larger_support_original_seeds_size=int(cf.sum()),
            support_only_changed_voxels=int((cf!=masks[6]).sum()),new_seed_effect_voxels=int((cf!=masks[8]).sum()))
        records.append(record)
        traced_masks[number]=masks
        # Orthogonal local projections, identical raw intensity window for both contexts.
        p=point-origin; x0=max(0,int(p[0])-14); x1=min(a.shape[0],int(p[0])+15)
        y0=max(0,int(p[1])-14); y1=min(a.shape[1],int(p[1])+15)
        raw=a[x0:x1,y0:y1,:]; low,high=np.percentile(raw,[2,99.5])
        fig,axes=b.plt.subplots(2,2,figsize=(10,7),constrained_layout=True)
        for col,h in enumerate([6,8]):
            m=masks[h][x0:x1,y0:y1,:]
            for rr,(im,overlay) in enumerate([(raw[:,:,int(p[2])].T,m[:,:,int(p[2])].T),(raw.max(axis=1).T,m.any(axis=1).T)]):
                axes[rr,col].imshow(im,cmap='gray',vmin=low,vmax=high,origin='lower',aspect='auto')
                axes[rr,col].imshow(np.ma.masked_where(~overlay,overlay),cmap='autumn',vmin=0,vmax=1,alpha=.55,origin='lower',aspect='auto')
                axes[rr,col].set_title(f'halo {h}: '+('XY at seed Z' if rr==0 else 'XZ projection across local Y'))
            axes[0,col].plot(p[0]-x0,p[1]-y0,'c+',ms=12)
            axes[1,col].plot(p[0]-x0,p[2],'c+',ms=12)
            axes[1,col].axhline(2 if h==6 else 0,color='cyan',ls=':')
            axes[1,col].axhline(17 if h==6 else 19,color='cyan',ls=':')
        fig.suptitle(f'Object {number}: seed {point.tolist()} | sizes {details["6"]["size"]} -> {details["8"]["size"]}\nOrange: assigned mask; cyan: seed/context limits. Projections are not cell labels.')
        fig.savefig(OUT/f'object{number}.png',dpi=140);b.plt.close(fig)
    lost=traced_masks[2][6]&~traced_masks[2][8]
    gained=traced_masks[3][8]&~traced_masks[3][6]
    assert np.array_equal(lost,gained) and int(lost.sum())==14
    report=dict(scope='Diagnostic counterfactual; unchanged thresholds, no biological scoring',
        pair_2_3_exact_transfer_voxels=14,objects=records)
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2))
    (OUT/'review.html').write_text('<html><meta charset="utf-8"><title>Seven depth-sensitive seeds</title><body style="background:#222;color:white;font-family:sans-serif"><h1>Seven depth-sensitive seeds</h1><p>These are algorithmic objects, not confirmed cells. Same intensity window per object. Local projections may overlap unrelated structures.</p>'+''.join(f'<h2>Object {r["object"]}</h2><img style="max-width:100%" src="object{r["object"]}.png"><pre>{b.json.dumps({k:x for k,x in r.items() if k!="contexts"},indent=2)}</pre>' for r in records)+'</body></html>')
    print(OUT,flush=True)
    for r in records: print({k:x for k,x in r.items() if k!='contexts'},[(h,d['size'],d['component_seed_count'],d['component_faces']) for h,d in r['contexts'].items()],flush=True)

if __name__=='__main__':run()
