"""Experimental fixed ownership, retained halo seeds and bounded context recovery."""
import validate_component_segmentation as v
b=v.b; np=b.np; e=v.e
ROOT=b.ROOT/'test-data/review2-blocks-20261026T114217189786Z'
OUT=b.ROOT/'test-data'/('block-ownership-'+b.run_stamp)

def evaluate(a,minimum,maximum,overlap,max_expansions=8):
    seeds=np.argwhere(a==1000); global_markers=e.markers(a.shape,seeds)
    reference=v.segment(-a.astype(float),global_markers,a>168)
    blocks=b.Cells.bp.split_into_blocks(b.Cells.clearmap_io.as_source(a),processes=1,
        size_min=minimum,size_max=maximum,overlap=overlap,axes=[2],optimization=True,optimization_fix='all',verbose=False)
    outputs=[]; traces=[]; seen=[]
    for index,block in enumerate(blocks):
        core_lo=np.array(block.lower)+block.valid.lower; core_hi=np.array(block.lower)+block.valid.upper
        owned=np.flatnonzero(np.all((seeds>=core_lo)&(seeds<core_hi),axis=1))
        if not len(owned): continue
        seen.extend(owned.tolist())
        lo=np.array(block.lower); hi=np.array(block.upper); steps=[]
        for attempt in range(max_expansions+1):
            sl=tuple(slice(int(l),int(h)) for l,h in zip(lo,hi))
            image=a[sl]; mask=image>168; components,_=b.ndi.label(mask)
            wanted={int(components[tuple(seeds[i]-lo)]) for i in owned}
            unsafe=[]; physical=[]
            for axis in range(a.ndim):
                for side in [0,1]:
                    face=[slice(None)]*a.ndim; face[axis]=0 if side==0 else -1
                    touched=wanted.intersection(set(np.unique(components[tuple(face)])))-{0}
                    if touched:
                        at_volume_edge=lo[axis]==0 if side==0 else hi[axis]==a.shape[axis]
                        (physical if at_volume_edge else unsafe).append((axis,side))
            steps.append(dict(lo=lo.tolist(),hi=hi.tolist(),artificial_faces=unsafe,physical_faces=physical))
            if not unsafe: break
            if attempt==max_expansions: break
            for axis,side in unsafe:
                step=max(overlap,8)
                if side==0: lo[axis]=max(0,lo[axis]-step)
                else: hi[axis]=min(a.shape[axis],hi[axis]+step)
        if unsafe:
            outputs.extend(dict(seed=seeds[i].tolist(),status='needs_context',size=None) for i in owned)
        else:
            # Include every seed in context, not only the owning core's seeds.
            result=v.segment(-image.astype(float),global_markers[sl],mask)
            for i in owned:
                label=int(i+1); local_pixels=np.argwhere(result==label)+lo
                expected=np.argwhere(reference==label)
                identical=np.array_equal(local_pixels,expected)
                # Physical edges require QC even when reference agrees.
                component=components[tuple(seeds[i]-lo)]
                touches_volume=False
                for axis,side in physical:
                    face=[slice(None)]*a.ndim; face[axis]=0 if side==0 else -1
                    touches_volume |= bool(np.any(components[tuple(face)]==component))
                outputs.append(dict(seed=seeds[i].tolist(),status='physical_edge_qc' if touches_volume else 'complete',
                    size=len(local_pixels),reference_size=len(expected),voxel_labels_match=identical))
        traces.append(dict(owner_block=index,owned_seed_ids=(owned+1).tolist(),expansions=len(steps)-1,steps=steps))
    assert sorted(seen)==list(range(len(seeds))), 'Missing or duplicate ownership'
    return dict(cells=outputs,owners=traces,unique_ownership=True,
                complete_labels_match=all(c.get('voxel_labels_match',False) for c in outputs))

def run():
    OUT.mkdir(); report={'threshold':168,'production_changes':False,
      'scope':'Synthetic shape-stage experiment with known peaks and actual ClearMap block ownership. No preprocessing/peak recall validation. Full arrays loaded for diagnostics; not a memory-scalable production runner.', 'cases':[]}
    for config,minimum,maximum,overlap in [('machine_cfg',10,16,5),('api_default',50,100,32)]:
        for kind in ['compact_before','compact_at','compact_after','extended','competing_across']:
            source=ROOT/f'{config}_{kind}.npy'; a=np.load(source)
            result=evaluate(a,minimum,maximum,overlap)
            assert result['complete_labels_match']
            report['cases'].append(dict(config=config,case=kind,input_sha256=b.hashlib.sha256(source.read_bytes()).hexdigest(),**result))
    a=np.load(ROOT/'machine_cfg_extended.npy')
    stopped=evaluate(a,10,16,5,max_expansions=0)
    assert any(c['status']=='needs_context' and c['size'] is None for c in stopped['cells'])
    report['budget_stop_control']=stopped
    a=np.zeros((25,25,80),np.uint16); a[10:15,10:15,:]=250; a[12,12,40]=1000
    edge=evaluate(a,10,16,5,max_expansions=12)
    assert all(c['status']=='physical_edge_qc' for c in edge['cells'])
    assert edge['complete_labels_match']
    report['physical_edge_control']=edge
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2))
    print(OUT)
    print(b.json.dumps([dict(config=c['config'],case=c['case'],sizes=[r['size'] for r in c['cells']],
        expansions=[o['expansions'] for o in c['owners']],exact_labels=c['complete_labels_match']) for c in report['cases']],indent=2))
    print('Budget-stop and physical-edge controls passed')

if __name__=='__main__': run()
