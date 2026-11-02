"""Separate context effects by stage; experimental diagnostics, no scoring."""
import validate_component_segmentation as v
import os
from test_canvas_context import CORE_LO, CORE_HI
b=v.b; np=b.np
OUT=b.ROOT/'test-data'/('canvas-stages-'+b.run_stamp)

def run():
    OUT.mkdir()
    extended=os.environ.get('CANVAS_DEPTH20')=='1'
    path=b.ROOT/'test-data/canvas-audit'/('depth20-zyx.npy' if extended else 'expanded-zyx.npy')
    a=np.load(path).transpose(2,1,0); origin=np.array([4382,3178,1126 if extended else 1130])
    halos=[4,6,8,8] if extended else [1,2,3,4]
    report=dict(source_sha256=b.hashlib.sha256(path.read_bytes()).hexdigest(),
        core_lower=CORE_LO.tolist(),core_upper=CORE_HI.tolist(),xy_halo=40,
        parameters=dict(background_shape=[21,21],background_form='Disk',maxima_shape=[11,11,1],threshold=168,h_max=None),
        scope='Same raw maxima for all segmentation variants; no plateau collapse, merging, threshold tuning or biological scoring.',runs=[],comparisons=[])
    previous=None
    report['z_halos']=halos
    (OUT/'plan.json').write_text(b.json.dumps(report,indent=2))
    previous_z=None
    for run_index,z in enumerate(halos):
        lo=CORE_LO-[40,40,z]; hi=CORE_HI+[40,40,z]
        assert np.all(lo>=origin) and np.all(hi<=origin+a.shape)
        sl=tuple(slice(int(l),int(h)) for l,h in zip(lo-origin,hi-origin))
        raw=np.asfortranarray(a[sl])
        corr=b.Cells.remove_background(raw,shape=(21,21),form='Disk')
        maxima=b.ORIGINAL(corr,shape=(11,11,1),threshold=168,h_max=None)
        seeds=b.Cells.ap.where(maxima,processes=1).array; global_seeds=seeds+lo
        owned=np.all((global_seeds>=CORE_LO)&(global_seeds<CORE_HI),axis=1)
        ids=np.flatnonzero(owned)+1
        core=tuple(slice(int(l),int(h)) for l,h in zip(CORE_LO-lo,CORE_HI-lo))
        mask=corr>168; components,_=b.ndi.label(mask)
        faces=np.unique(np.concatenate([np.take(components,i,axis=ax).ravel() for ax in range(3) for i in [0,-1]]))
        zfaces=np.unique(np.concatenate([components[:,:,0].ravel(),components[:,:,-1].ravel()]))
        seed_components=components[tuple(seeds[owned].T)]
        table=b.pd.DataFrame(global_seeds[owned],columns=['x','y','z'])
        table['in_foreground']=seed_components>0
        table['touches_face']=(seed_components>0)&np.isin(seed_components,faces)
        table['touches_z_face']=(seed_components>0)&np.isin(seed_components,zfaces)
        markers=v.e.markers(corr.shape,seeds)
        labels={}
        for name in ['native','direct_global','direct_component']:
            if name=='native': result=v.e.original(corr,seeds,threshold=168,processes=1)
            elif name=='direct_global': result=v.watershed(-corr,markers,mask=mask)
            else: result=v.segment(-corr,markers,mask)
            sizes=np.bincount(result.ravel().astype(np.int64),minlength=len(seeds)+1)
            table[name]=sizes[ids]
            # Encode labels using stable global seed coordinates; invalid native IDs get -1.
            mapping=np.full(max(len(sizes),len(seeds)+1),-1,dtype=np.int64); mapping[0]=0
            mapping[1:len(seeds)+1]=np.ravel_multi_index((global_seeds-origin).T,a.shape)+1
            labels[name]=mapping[result[core].astype(np.int64)]
        table.to_csv(OUT/f'run{run_index}_z{z}_core.csv',index=False)
        np.savez_compressed(OUT/f'run{run_index}_z{z}_core_stages.npz',corrected=corr[core],maxima=maxima[core],**labels)
        report['runs'].append(dict(z_halo=z,core_peaks=len(table),core_peaks_touching_face=int(table.touches_face.sum()),distinct_core_components_touching_face=int(len(np.unique(seed_components[table.touches_face.to_numpy()]))),core_peaks_touching_z_face=int(table.touches_z_face.sum()),retained={name:int((table[name]>0).sum()) for name in labels}))
        if previous is not None:
            old_corr,old_max,old_table,old_labels=previous
            joined=old_table.merge(table,on=['x','y','z'],suffixes=('_old','_new'))
            changes={}
            for name in labels:
                changed=joined[name+'_old']!=joined[name+'_new']
                closed=joined.in_foreground_old&joined.in_foreground_new&~(joined.touches_face_old|joined.touches_face_new)
                changes[name]=dict(size_changes=int(changed.sum()),size_changes_closed_components=int((changed&closed).sum()),core_assignment_voxel_changes=int(np.count_nonzero(old_labels[name]!=labels[name])))
            report['comparisons'].append(dict(z_halos=[previous_z,z],corrected_voxel_changes=int(np.count_nonzero(old_corr!=corr[core])),maxima_voxel_changes=int(np.count_nonzero(old_max!=maxima[core])),common_peaks=len(joined),segmentation=changes))
        previous=(corr[core].copy(),maxima[core].copy(),table,labels)
        previous_z=z
        print(report['runs'][-1],flush=True)
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2))
    print(OUT, b.json.dumps(report['comparisons'],indent=2),flush=True)

if __name__=='__main__': run()

