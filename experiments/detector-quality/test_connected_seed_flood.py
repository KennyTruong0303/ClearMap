"""Experimental connected flood: equal-cost fronts stop as explicit uncertainty."""
import heapq,itertools
import test_canvas_physical_ties as t
b=t.b;np=t.np
ROOT=t.s.ROOT;OUT=ROOT/('connected-flood-'+b.run_stamp)

def flood(im,mask,markers,steps,ceiling_override=None,cost_rule='component_max'):
    # Positive additive edge cost guarantees all equal-time proposals arrive
    # before settlement. This is a new objective, not watershed equivalence.
    labels=markers.copy();state=np.where(mask,0,3).astype(np.uint8)
    state[markers>0]=1;queue=[];ceiling=int(im[mask].max()) if mask.any() else 0
    if ceiling_override is not None:
        ceiling=int(ceiling_override)
    def propose(p,lab,cost):
        for ax in range(mask.ndim):
            for sign in [-1,1]:
                q=list(p);q[ax]+=sign;q=tuple(q)
                if all(0<=q[i]<mask.shape[i] for i in range(mask.ndim)) and state[q]==0:
                    if cost_rule=='local_gradient':
                        edge=int(steps[ax])*(1+abs(int(im[p])-int(im[q])))
                    elif cost_rule=='component_max':
                        edge=int(steps[ax])*(1+ceiling-min(int(im[p]),int(im[q])))
                    else:raise ValueError(cost_rule)
                    heapq.heappush(queue,(cost+edge,q,int(lab)))
    for p in np.argwhere(markers>0):
        p=tuple(p);propose(p,labels[p],0)
    while queue:
        cost=queue[0][0];batch={}
        while queue and queue[0][0]==cost:
            _,p,lab=heapq.heappop(queue)
            if state[p]==0:batch.setdefault(p,set()).add(lab)
        settled=[]
        for p,labs in batch.items():
            if len(labs)>1:state[p]=2
            else:
                labels[p]=next(iter(labs));state[p]=1;settled.append(p)
        for p in settled:propose(p,labels[p],cost)
    return labels,state==2,mask&(state==0)

def invariants(labels,tied,unreached,m,mask):
    assert np.array_equal(labels[m>0],m[m>0])
    assert np.all((labels[mask]>0)|tied[mask]|unreached[mask])
    assert not np.any(labels[~mask])
    for lab in np.unique(m[m>0]):
        cc,_=b.ndi.label(labels==lab);p=tuple(np.argwhere(m==lab)[0])
        assert np.all(cc[labels==lab]==cc[p])

def run():
    OUT.mkdir();source=ROOT/'physical-ties-challenge-20261030T133638544441Z'
    prior=b.json.loads((source/'report.json').read_text())
    report=dict(definition='Connected multi-source additive flood. Edge cost = integer axis distance * (1 + component maximum intensity - minimum endpoint intensity). Simultaneous equal-cost proposals from distinct seeds become ties and do not propagate. Unreachable voxels remain separately unresolved. Seeds never merge. This intensity weighting is experimental, not tuned or biologically validated.',regions=[])
    for row in prior['regions']:
        name=row['name'];d=np.load(source/(name+'.npz'));im=d['intensity'];mask=d['mask'];m=d['markers']
        steps=np.ones(3,dtype=int) if name.startswith('demo') else np.array([18,18,40])
        result=flood(im,mask,m,steps);invariants(*result,m,mask);fail=0
        for perm in itertools.permutations(range(3)):
            for flips in itertools.product([False,True],repeat=3):
                axes=tuple(i for i,f in enumerate(flips) if f)
                def f(x):return np.flip(x.transpose(perm),axis=axes)
                transformed=flood(f(im),f(mask),f(m),steps[list(perm)])
                def undo(x):return np.flip(x,axis=axes).transpose(np.argsort(perm))
                fail+=not all(np.array_equal(a,undo(c)) for a,c in zip(result,transformed))
        maximum=int(m.max())+1;reversed_m=np.where(m>0,maximum-m,0)
        rev=flood(im,mask,reversed_m,steps);rev=(np.where(rev[0]>0,maximum-rev[0],0),rev[1],rev[2])
        assert all(np.array_equal(x,y) for x,y in zip(result,rev))
        assert all(np.array_equal(x,y) for x,y in zip(result,flood(im,mask,m,steps)))
        labels,tied,unreached=result
        record=dict(name=name,voxels=int(mask.sum()),tied=int(tied.sum()),unreached=int(unreached.sum()),detached_voxels=0,orientation_tests=48,orientation_failures=int(fail),relabel_and_repeat_pass=True,changed_vs_watershed=int((labels!=d['baseline']).sum()))
        if name=='original_pair':
            record['seed_additions']={}
            for case,remove in [('old_only',[17,18]),('new_A',[18]),('new_B',[17]),('both',[])]:
                mm=m.copy();mm[np.isin(mm,remove)]=0;r=flood(im,mask,mm,steps);invariants(*r,mm,mask)
                record['seed_additions'][case]=dict(pair_sizes=[int((r[0]==i).sum()) for i in [8,9]],pair_mask_changes_vs_both=int(np.count_nonzero(((r[0]==8)!=(labels==8))|((r[0]==9)!=(labels==9)))))
        report['regions'].append(record);np.savez_compressed(OUT/(name+'.npz'),labels=labels,tied=tied,unreached=unreached)
        print(record,flush=True)
    flat=np.ones((5,5,3));mask=np.ones(flat.shape,bool);m=np.zeros(flat.shape,np.int32);m[0,2,1]=1;m[4,2,1]=2
    r=flood(flat,mask,m,np.array([18,18,40]));invariants(*r,m,mask);assert np.all(r[1][2,:,:]) and r[1].sum()==15
    m[:]=0;m[0,2,1]=1;r=flood(flat,mask,m,np.array([18,18,40]));assert np.all(r[0]==1)
    report['synthetic_symmetric_tie_and_single_seed_pass']=True
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2));print(OUT,flush=True)

if __name__=='__main__':run()
