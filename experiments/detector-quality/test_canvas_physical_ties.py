"""Physical mask-geodesic distance breaks maximin ties; exact ties stay unknown."""
import test_canvas_saddle_policy as s
b=s.b; np=s.np
OUT=s.ROOT/('canvas-physical-ties-'+b.run_stamp)

def distance(mask,seed,steps):
    d=np.full(mask.shape,np.iinfo(np.int64).max,dtype=np.int64)
    p=tuple(seed);d[p]=0;queue=[(0,p)]
    while queue:
        value,p=s.heapq.heappop(queue)
        if value!=d[p]:continue
        for ax in range(mask.ndim):
            for sign in [-1,1]:
                q=list(p);q[ax]+=sign;q=tuple(q)
                if all(0<=q[i]<mask.shape[i] for i in range(mask.ndim)) and mask[q]:
                    candidate=value+int(steps[ax])
                    if candidate<d[q]:d[q]=candidate;s.heapq.heappush(queue,(candidate,q))
    return d

def policy(intensity,mask,markers,steps):
    ids=np.unique(markers[markers>0]);points=[np.argwhere(markers==i)[0] for i in ids]
    scores=np.stack([s.capacities(intensity,mask,p) for p in points]);tied=scores==scores.max(0)
    distances=np.stack([distance(mask,p,steps) for p in points])
    distances=np.where(tied,distances,np.iinfo(np.int64).max)
    winners=tied&(distances==distances.min(0));amb=mask&(winners.sum(0)>1)
    labels=np.where(mask,ids[distances.argmin(0)],0);labels[amb]=0
    labels[markers>0]=markers[markers>0];amb[markers>0]=False
    return labels,amb

def run():
    OUT.mkdir();source=s.ROOT/'canvas-seed-competition-20261030T085842709966Z'
    data=np.load(source/'component.npz');prior=b.json.loads((source/'report.json').read_text())
    trace=b.json.loads((s.ROOT/'canvas-trace-20261030T074555869523Z/report.json').read_text())
    origin=np.array(trace['objects'][1]['contexts']['8']['component_bounds_lower'])
    coords=data['global_seeds']-origin;mask=data['mask'];im=np.negative(data['image']).astype(float)
    steps=np.array([18,18,40]);pair=prior['pair_ids'];outputs={}
    report=dict(definition='First maximize minimum path intensity. Among equal-scoring seeds, minimize shortest face-connected path length through the foreground mask. The distance path need not realize the maximum bottleneck. Preserve equal distance ambiguity and seed identity. Distinct experimental objective, not equivalent to watershed.',spacing_xyz_um=[1.8,1.8,4],spacing_source='Published CANVAS acquisition; TIFF physical calibration unverified',integer_distance_unit_um=0.1,cases={})
    for name,indices in {'old_only':list(range(16)),'new_A':list(range(17)),'new_B':list(range(16))+[17],'both':list(range(18))}.items():
        m=np.zeros(mask.shape,np.int32);m[tuple(coords[indices].T)]=np.array(indices)+1
        ref,amb=policy(im,mask,m,steps);outputs[name]=(ref,amb);failures=[]
        for perm in s.itertools.permutations(range(3)):
            for flips in s.itertools.product([False,True],repeat=3):
                axes=tuple(i for i,f in enumerate(flips) if f)
                def f(x):return np.flip(x.transpose(perm),axis=axes)
                r,u=policy(f(im),f(mask),f(m),steps[list(perm)])
                def undo(x):return np.flip(x,axis=axes).transpose(np.argsort(perm))
                if not np.array_equal(ref,undo(r)) or not np.array_equal(amb,undo(u)):failures.append([list(perm),list(flips)])
        r,u=policy(im,mask,np.where(m>0,19-m,0),steps);r=np.where(r>0,19-r,0)
        assert np.array_equal(r,ref) and np.array_equal(u,amb)
        assert np.array_equal(ref[m>0],m[m>0]) and np.all((ref[mask]>0)|amb[mask])
        transfer=(data['old_only']==pair[0])&(data['both']==pair[1])
        report['cases'][name]=dict(pair_sizes=[int((ref==i).sum()) for i in pair],ambiguous_voxels=int(amb.sum()),transfer_ambiguous=int((amb&transfer).sum()),transfer_pair_assignments=[int(((ref==i)&transfer).sum()) for i in pair],orientation_tests=48,orientation_failures=failures,relabel_invariant=True)
        np.savez_compressed(OUT/(name+'.npz'),labels=ref,ambiguous=amb)
        print(name,report['cases'][name],flush=True)
    report['pair_changes_vs_original']={name:int(np.count_nonzero(np.isin(outputs[name][0],pair)&(outputs[name][0]!=outputs['old_only'][0]))) for name in outputs}
    # Equal physical distance plane must stay ambiguous. Z spacing must matter.
    flat=np.ones((3,3,3));ms=np.ones(flat.shape,bool);m=np.zeros(flat.shape,np.int32);m[0,1,1]=1;m[2,1,1]=2
    r,u=policy(flat,ms,m,steps);assert np.all(u[1,:,:]) and u.sum()==9
    m[:]=0;m[0,1,1]=1;m[1,1,0]=2
    r,u=policy(flat,ms,m,steps);assert r[1,1,1]==1 and not u[1,1,1]
    r,u=policy(flat,ms,m,np.ones(3,dtype=int));assert u[1,1,1]
    report['synthetic_equal_distance_and_anisotropy_passed']=True
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2));print(OUT,flush=True)

if __name__=='__main__':run()
