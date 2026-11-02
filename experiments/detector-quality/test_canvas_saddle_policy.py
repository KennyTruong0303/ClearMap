"""Conservative maximin-connectivity diagnostic; tied winners remain ambiguous."""
import heapq,itertools,time
import validate_component_segmentation as v
b=v.b; np=b.np
ROOT=b.ROOT/'test-data'; OUT=ROOT/('canvas-saddle-'+b.run_stamp)

def capacities(intensity,mask,seed):
    best=np.full(mask.shape,-np.inf); p=tuple(seed); best[p]=float(intensity[p]); queue=[(-best[p],p)]
    while queue:
        neg,p=heapq.heappop(queue); value=-neg
        if value<best[p]:continue
        for axis in range(mask.ndim):
            for sign in [-1,1]:
                q=list(p);q[axis]+=sign;q=tuple(q)
                if all(0<=q[d]<mask.shape[d] for d in range(mask.ndim)) and mask[q]:
                    candidate=min(value,float(intensity[q]))
                    if candidate>best[q]:
                        best[q]=candidate;heapq.heappush(queue,(-candidate,q))
    return best

def policy(intensity,mask,markers):
    ids=np.unique(markers[markers>0]); scores=np.stack([capacities(intensity,mask,np.argwhere(markers==i)[0]) for i in ids])
    top=scores.max(0); winners=scores==top
    ambiguous=mask&(winners.sum(0)>1)
    result=np.where(mask,ids[scores.argmax(0)],0);result[ambiguous]=0
    # Seed identity is an explicit constraint, not a queue tie-break.
    result[markers>0]=markers[markers>0];ambiguous[markers>0]=False
    return result,ambiguous

def run():
    OUT.mkdir(); source=ROOT/'canvas-seed-competition-20261030T085842709966Z'
    data=np.load(source/'component.npz'); prior=b.json.loads((source/'report.json').read_text())
    trace=b.json.loads((ROOT/'canvas-trace-20261030T074555869523Z/report.json').read_text())
    origin=np.array(trace['objects'][1]['contexts']['8']['component_bounds_lower'])
    coords=data['global_seeds']-origin; mask=data['mask']; intensity=np.negative(data['image']).astype(float)
    # Recover the original uint16 corrected image before converting to float:
    # saved watershed input was negated in its original dtype.
    pair=prior['pair_ids']; p,q=[coords[i-1] for i in pair]
    saddle=float(capacities(intensity,mask,p)[tuple(q)])
    at,_=b.ndi.label(mask&(intensity>=saddle))
    above,_=b.ndi.label(mask&(intensity>saddle))
    assert at[tuple(p)]==at[tuple(q)] and at[tuple(p)]>0
    assert above[tuple(p)]!=above[tuple(q)]
    report=dict(definition='For each seed, maximize the minimum corrected intensity along face-connected paths. Unique best seed wins; equal best seeds yield explicit ambiguity. Preserve seed voxels. No distance or ID tie-break, no merging. This changes watershed semantics and is not a production replacement.',
        seed_heights=[float(intensity[tuple(x)]) for x in [p,q]],connecting_saddle=saddle,
        foreground_voxels=int(mask.sum()),cases={})
    for name,indices in {'old_only':list(range(16)),'new_A':list(range(17)),'new_B':list(range(16))+[17],'both':list(range(18))}.items():
        markers=np.zeros(mask.shape,np.int32);markers[tuple(coords[indices].T)]=np.array(indices)+1
        start=time.perf_counter(); ref,amb=policy(intensity,mask,markers); failures=[]
        for perm in itertools.permutations(range(3)):
            for flips in itertools.product([False,True],repeat=3):
                axes=tuple(i for i,f in enumerate(flips) if f)
                def f(a):return np.flip(a.transpose(perm),axis=axes)
                r,u=policy(f(intensity),f(mask),f(markers))
                def undo(a):return np.flip(a,axis=axes).transpose(np.argsort(perm))
                if not np.array_equal(ref,undo(r)) or not np.array_equal(amb,undo(u)):failures.append([list(perm),list(flips)])
        reverse=np.where(markers>0,19-markers,0);r,u=policy(intensity,mask,reverse);r=np.where(r>0,19-r,0)
        assert np.array_equal(r,ref) and np.array_equal(u,amb)
        assert np.array_equal(ref[markers>0],markers[markers>0])
        assert np.all((ref[mask]>0)|amb[mask]) and not np.any(ref[~mask])
        transfer=(data['old_only']==pair[0])&(data['both']==pair[1])
        report['cases'][name]=dict(pair_assigned_sizes=[int((ref==i).sum()) for i in pair],ambiguous_voxels=int(amb.sum()),transfer_ambiguous_voxels=int((amb&transfer).sum()),orientation_failures=failures,orientation_tests=48,relabel_invariant=True,elapsed_seconds=time.perf_counter()-start)
        np.savez_compressed(OUT/(name+'.npz'),labels=ref,ambiguous=amb)
        print(name,report['cases'][name],flush=True)
    # Known symmetric tied foreground must remain ambiguous away from preserved seeds.
    flat=np.ones((3,3,3));m=np.zeros(flat.shape,np.int32);m[0,1,1]=1;m[2,1,1]=2
    r,u=policy(flat,np.ones(flat.shape,bool),m);assert u.sum()==25 and (r>0).sum()==2
    report['flat_synthetic_passed']=True
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2));print(OUT,report['seed_heights'],saddle,flush=True)

if __name__=='__main__':run()
