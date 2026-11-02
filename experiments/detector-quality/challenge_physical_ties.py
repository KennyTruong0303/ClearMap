"""Third-seed attribution and bounded additional-region challenge."""
import test_canvas_physical_ties as t
b=t.b;np=t.np;v=t.s.v
ROOT=t.s.ROOT;OUT=ROOT/('physical-ties-challenge-'+b.run_stamp)

def check(name,im,mask,m,steps,closed):
    ref,amb=t.policy(im,mask,m,steps);fail=0
    for perm in t.s.itertools.permutations(range(3)):
        for flips in t.s.itertools.product([False,True],repeat=3):
            axes=tuple(i for i,f in enumerate(flips) if f)
            def f(x):return np.flip(x.transpose(perm),axis=axes)
            r,u=t.policy(f(im),f(mask),f(m),steps[list(perm)])
            def undo(x):return np.flip(x,axis=axes).transpose(np.argsort(perm))
            fail+=not(np.array_equal(ref,undo(r)) and np.array_equal(amb,undo(u)))
    detached={}
    for i in np.unique(m[m>0]):
        cc,_=b.ndi.label(ref==i);p=tuple(np.argwhere(m==i)[0]);n=int(np.count_nonzero((ref==i)&(cc!=cc[p])))
        if n:detached[str(i)]=n
    baseline=v.segment(-im,m,mask)
    baseline_detached={}
    for i in np.unique(m[m>0]):
        cc,_=b.ndi.label(baseline==i);p=tuple(np.argwhere(m==i)[0])
        baseline_detached[str(int(i))]=int(np.count_nonzero((baseline==i)&(cc!=cc[p])))
    assert np.array_equal(ref[m>0],m[m>0])
    np.savez_compressed(OUT/(name+'.npz'),intensity=im,mask=mask,markers=m,labels=ref,ambiguous=amb,baseline=baseline)
    return dict(name=name,closed=closed,voxels=int(mask.sum()),seeds=int(np.count_nonzero(m)),ambiguous=int(amb.sum()),orientation_failures=int(fail),orientation_tests=48,changed_vs_component_watershed=int(np.count_nonzero(ref!=baseline)),detached_assignment_voxels=detached,baseline_detached_assignment_voxels=baseline_detached)

def run():
    OUT.mkdir();report=dict(scope='Computational diagnostic, no biological scoring or production changes',regions=[],third_seed={})
    src=ROOT/'canvas-seed-competition-20261030T085842709966Z';d=np.load(src/'component.npz')
    prev=b.json.loads((src/'report.json').read_text());trace=b.json.loads((ROOT/'canvas-trace-20261030T074555869523Z/report.json').read_text())
    origin=np.array(trace['objects'][1]['contexts']['8']['component_bounds_lower']);coords=d['global_seeds']-origin
    im=np.negative(d['image']).astype(float);mask=d['mask'];steps=np.array([18,18,40]);m=np.zeros(mask.shape,np.int32);m[tuple(coords.T)]=np.arange(1,19)
    labels,amb=t.policy(im,mask,m,steps);pair=prev['pair_ids'];transfer=(d['old_only']==pair[0])&(d['both']==pair[1]);six=transfer&(labels==10)
    assert six.sum()==6
    score=np.stack([t.s.capacities(im,mask,p) for p in coords]);dist=np.stack([t.distance(mask,p,steps) for p in coords])
    rows=[]
    for p in np.argwhere(six):
        ix=tuple(p); top=score[(slice(None),)+ix].max();eligible=np.flatnonzero(score[(slice(None),)+ix]==top)
        rows.append(dict(xyz=(p+origin).tolist(),intensity=float(im[ix]),eligible_seed_ids=(eligible+1).tolist(),eligible_distances_um=(dist[(eligible,)+ix]/10).tolist()))
    cc,_=b.ndi.label(labels==10);seedcc=cc[tuple(coords[9])]
    report['third_seed']=dict(xyz=d['global_seeds'][9].tolist(),height=float(im[tuple(coords[9])]),assigned_size=int((labels==10).sum()),six_connected_to_seed=bool(np.all(cc[six]==seedcc)),voxels=rows)
    # Exact XY slices: cyan pair, green third seed, red six reassigned voxels, yellow ambiguity.
    zs=sorted(set(np.argwhere(six)[:,2])|{int(coords[i-1,2]) for i in pair+[10]})
    fig,axes=b.plt.subplots(1,len(zs),figsize=(4*len(zs),5),squeeze=False,constrained_layout=True)
    for ax,z in zip(axes[0],zs):
        ax.imshow(im[:,:,z].T,cmap='gray',origin='lower')
        overlay=np.zeros(im.shape[:2]+(4,));overlay[amb[:,:,z]]=[1,1,0,.5];overlay[six[:,:,z]]=[1,0,0,.9]
        ax.imshow(overlay.transpose(1,0,2),origin='lower')
        for i in pair+[10]:
            p=coords[i-1]
            if p[2]==z:ax.plot(p[0],p[1],'+',color='lime' if i==10 else 'cyan',ms=12);ax.text(p[0]+.3,p[1],str(i),color='lime' if i==10 else 'cyan')
        ax.set_title(f'global Z {z+origin[2]}')
    fig.suptitle('Corrected intensity | red: six voxels | yellow: ambiguous | green: third seed\nLocal voxel coordinates; diagnostic seeds are not confirmed cells')
    fig.savefig(OUT/'third-seed.png',dpi=150);b.plt.close(fig)
    report['regions'].append(check('original_pair',im,mask,m,steps,False))
    def select(name,raw,steps,count):
        corr=b.Cells.remove_background(np.asfortranarray(raw),shape=(21,21),form='Disk')
        peaks=b.ORIGINAL(corr,shape=(11,11,1),threshold=168,h_max=None)
        if name.startswith('demo'):
            peaks=b.collapse_plateaus(corr,peaks)
        cc,_=b.ndi.label(corr>168);chosen=0
        for cid,sl in enumerate(b.ndi.find_objects(cc),1):
            if sl is None:continue
            local=cc[sl]==cid;points=np.argwhere(peaks[sl]&local)
            if not(30<=local.sum()<=700 and 2<=len(points)<=8):continue
            closed=all(sl[ax].start>0 and sl[ax].stop<raw.shape[ax] for ax in range(3) if raw.shape[ax]>1)
            if not closed:continue
            markers=t.s.v.e.markers(local.shape,points)
            row=check(f'{name}_{cid}',corr[sl].astype(float),local,markers,steps,True);row['bounds_local']=[[s.start,s.stop] for s in sl];report['regions'].append(row)
            print(row,flush=True);chosen+=1
            if chosen==count:break
        report.setdefault('selection',{})[name]=dict(requested=count,found=chosen,plateaus_collapsed=name.startswith('demo'))
    raw=np.load(ROOT/'canvas-audit/depth20-zyx.npy').transpose(2,1,0)
    select('canvas',raw,steps,4)
    # Earlier geodesic-failure demo crops; unit grid is an algorithmic 2D test, not assumed physical spacing.
    for number in [25,26]:
        data=b.tifffile.imread(ROOT/f'neatmap/RawImage_example/RawImage_merged_{number}.tif')[5,0]
        select(f'demo{number}',data[200:456,800:1056].T[:,:,None],np.ones(3,dtype=int),2)
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2));print(OUT,report['third_seed'],flush=True)

if __name__=='__main__':run()
