"""Fixed-support seed ablation and orientation challenge; never merges seeds."""
import itertools
import validate_component_segmentation as v
b=v.b; np=b.np
ROOT=b.ROOT/'test-data'; OUT=ROOT/('canvas-seed-competition-'+b.run_stamp)

def run():
    OUT.mkdir()
    trace=b.json.loads((ROOT/'canvas-trace-20261030T074555869523Z/report.json').read_text())
    obj=trace['objects'][1]; origin=np.array([4382,3178,1126])
    a=np.asfortranarray(np.load(ROOT/'canvas-audit/depth20-zyx.npy').transpose(2,1,0))
    corr=b.Cells.remove_background(a,shape=(21,21),form='Disk')
    cc,_=b.ndi.label(corr>168); p=np.array(obj['seed_xyz'])-origin
    mask=cc==cc[tuple(p)]; points=np.argwhere(mask)
    lower=points.min(0); upper=points.max(0)+1
    sl=tuple(slice(int(l),int(h)) for l,h in zip(lower,upper))
    mask=mask[sl]; image=-corr[sl]
    old=np.array(obj['contexts']['6']['component_seeds_xyz'])
    all_seeds=np.array(obj['contexts']['8']['component_seeds_xyz'])
    new=np.array([s for s in all_seeds if tuple(s) not in set(map(tuple,old))])
    assert len(old)==16 and len(new)==2
    seeds=np.concatenate([old,new]); local=seeds-origin-lower
    pair=[int(np.flatnonzero(np.all(seeds==q,axis=1))[0])+1 for q in [obj['seed_xyz'],trace['objects'][2]['seed_xyz']]]
    cases={'old_only':list(range(16)),'new_A':list(range(17)),'new_B':list(range(16))+[17],'both':list(range(18))}
    report=dict(new_seeds_xyz=new.tolist(),pair_ids=pair,scope='Fixed foreground component and corrected image; stable categorical IDs; no merging, threshold change or biological inference.',cases={})
    outputs={}
    for name,indices in cases.items():
        markers=np.zeros(mask.shape,np.int32)
        markers[tuple(local[indices].T)]=np.array(indices)+1
        result=v.watershed(image,markers,mask=mask); outputs[name]=result
        reverse=np.where(markers>0,19-markers,0)
        rev_result=v.watershed(image,reverse,mask=mask)
        rev_result=np.where(rev_result>0,19-rev_result,0)
        trials=[]
        for perm in itertools.permutations(range(3)):
            for flips in itertools.product([False,True],repeat=3):
                def forward(x):
                    x=x.transpose(perm)
                    return np.flip(x,axis=tuple(i for i,f in enumerate(flips) if f))
                r=v.watershed(np.ascontiguousarray(forward(image)),np.ascontiguousarray(forward(markers)),mask=np.ascontiguousarray(forward(mask)))
                r=np.flip(r,axis=tuple(i for i,f in enumerate(flips) if f)).transpose(np.argsort(perm))
                pair_diff=int(np.count_nonzero(((r==pair[0])!=(result==pair[0]))|((r==pair[1])!=(result==pair[1]))))
                trials.append(dict(permutation=list(perm),flips=list(flips),changed_voxels=int(np.count_nonzero(r!=result)),pair_changed_voxels=pair_diff,pair_sizes=[int((r==i).sum()) for i in pair]))
        report['cases'][name]=dict(pair_sizes=[int((result==i).sum()) for i in pair],
            relabel_changed_voxels=int(np.count_nonzero(rev_result!=result)),
            repeat_equal=bool(np.array_equal(result,v.watershed(image,markers,mask=mask))),
            orientations=trials)
    assert report['cases']['old_only']['pair_sizes']==[22,3]
    assert report['cases']['both']['pair_sizes']==[8,17]
    base=outputs['old_only']; transfer=(base==pair[0])&(outputs['both']==pair[1])
    assert int(transfer.sum())==14
    report['transfer_corrected_values']=np.unique(corr[sl][transfer]).tolist()
    for name,r in outputs.items():
        report['cases'][name]['transfer_voxels_assigned_to_pair_second']=int(np.count_nonzero(transfer&(r==pair[1])))
        report['cases'][name]['transfer_voxels_assigned_to_new_seeds']=int(np.count_nonzero(transfer&(r>16)))
    np.savez_compressed(OUT/'component.npz',image=image,mask=mask,global_seeds=seeds,**outputs)
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2))
    print(OUT)
    print('New seeds',new.tolist(),'transfer values',report['transfer_corrected_values'])
    for name,c in report['cases'].items():
        print(name,{k:x for k,x in c.items() if k!='orientations'},'orientation failures',sum(t['changed_voxels']>0 for t in c['orientations']),'pair failures',sum(t['pair_changed_voxels']>0 for t in c['orientations']),'pair outcomes',sorted(set(tuple(t['pair_sizes']) for t in c['orientations'])))

if __name__=='__main__':run()
