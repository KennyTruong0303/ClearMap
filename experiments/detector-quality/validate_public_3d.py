"""Real 3D sample: actual preprocessing/peaks, fixed ownership and context recovery."""
import validate_component_segmentation as v
b=v.b; np=b.np; e=v.e
OUT=b.ROOT/'test-data'/('public-3d-validation-'+b.run_stamp)

def process(a):
    corrected=b.Cells.remove_background(a,shape=(21,21),form='Disk')
    peaks=b.md.find_maxima(corrected,shape=(11,11,1),threshold=168,h_max=None)
    coords=np.argwhere(b.collapse_plateaus(corrected,peaks))
    labels=v.segment(-corrected.astype(float),e.markers(a.shape,coords),corrected>168)
    return corrected,coords,labels

def shape(source,seeds,threshold=None,verbose=False,processes=None):
    a=e.sd.io.as_source(source).array; seeds=e.sd.io.as_source(seeds).array
    return v.segment(-a.astype(float),e.markers(a.shape,seeds),a>threshold)

def full_detector(path,proc):
    original=(b.Cells.detect_cells_block,b.md.find_maxima,e.sd.detect_shape)
    try:
        b.Cells.detect_cells_block=b.single_thread_block; b.md.find_maxima=b.experimental_maxima; e.sd.detect_shape=shape
        p=b.copy.deepcopy(b.Cells.default_cell_detection_parameter)
        p.update(illumination_correction=None,equalization=None,dog_filter=None)
        p['background_correction']['shape']=(21,21)
        p['maxima_detection'].update(shape=(11,11,1),threshold=168,h_max=None)
        p['shape_detection']['threshold']=168; p['intensity_detection']['measure']=['source']
        return b.pd.DataFrame(b.Cells.detect_cells(str(path),sink=None,cell_detection_parameter=p,processing_parameter=proc))
    finally:
        b.Cells.detect_cells_block,b.md.find_maxima,e.sd.detect_shape=original

def run():
    OUT.mkdir(); source=b.ROOT/'test-data/public-cellfinder-3d/ch0_zyx.npy'; stack=np.load(source,mmap_mode='r')
    report={'source_sha256':b.hashlib.sha256(source.read_bytes()).hexdigest(), 'axes':'XYZ after transposing source ZYX',
      'voxel_xyz_um':[2,2,5], 'parameters':{'background':[21,21],'maxima':[11,11,1],'threshold':168,'overlap':5,'size_min':10,'size_max':16},
      'scope':'Real 30-plane public sample, three predefined 96x96 XY crops, no manual ground truth. Existing settings frozen; z=1 peak neighborhood retained, not calibrated for this sample. Actual background removal and peak detection re-run in every context. All data loaded locally; not out-of-core scaling validation.', 'crops':[]}
    proc=dict(processes=1,size_min=10,size_max=16,overlap=5,axes=[2],optimization=True,optimization_fix='all',verbose=False)
    fig,axes=b.plt.subplots(3,3,figsize=(10,9),constrained_layout=True)
    for index,(x,y) in enumerate([(128,128),(288,256),(480,352)]):
        name=f'x{x}_y{y}'; a=np.asfortranarray(stack[:,y:y+96,x:x+96].transpose(2,1,0)); path=OUT/(name+'.npy'); np.save(path,a)
        corrected,seeds,reference=process(a)
        expected={tuple(p):np.argwhere(reference==i+1) for i,p in enumerate(seeds)}
        blocks=b.Cells.bp.split_into_blocks(b.Cells.clearmap_io.as_source(a),**proc)
        output={}; traces=[]; discoveries=0
        for block in blocks:
            lo=np.array(block.lower); hi=np.array(block.upper)
            core_lo=np.array(block.lower)+block.valid.lower; core_hi=np.array(block.lower)+block.valid.upper
            steps=[]; first_seeds=set()
            for attempt in range(6):
                sl=tuple(slice(int(l),int(h)) for l,h in zip(lo,hi))
                local,points,labels=process(a[sl]); components,_=b.ndi.label(local>168)
                core_sl=tuple(slice(int(l),int(h)) for l,h in zip(core_lo-lo,core_hi-lo))
                relevant=set(np.unique(components[core_sl]))-{0}; unsafe=[]
                for axis in range(3):
                    for side in [0,1]:
                        if (lo[axis]==0 if side==0 else hi[axis]==a.shape[axis]): continue
                        face=[slice(None)]*3; face[axis]=0 if side==0 else -1
                        if relevant.intersection(set(np.unique(components[tuple(face)]))): unsafe.append((axis,side))
                global_points=points+lo
                if attempt==0: first_seeds=set(map(tuple,global_points))
                steps.append(dict(lo=lo.tolist(),hi=hi.tolist(),seeds=len(points),artificial_faces=unsafe))
                if not unsafe: break
                if attempt==5: raise RuntimeError('Context budget exhausted; no result accepted')
                for axis,side in unsafe:
                    if side==0: lo[axis]=max(0,lo[axis]-8)
                    else: hi[axis]=min(a.shape[axis],hi[axis]+8)
            discoveries+=len(set(map(tuple,global_points))-first_seeds)
            take=np.all((global_points>=core_lo)&(global_points<core_hi),axis=1)
            for i in np.flatnonzero(take):
                p=tuple(global_points[i]); assert p not in output,'Duplicate ownership'
                output[p]=np.argwhere(labels==i+1)+lo
            traces.append(dict(core_lo=core_lo.tolist(),core_hi=core_hi.tolist(),steps=steps))
        coordinate_match=set(output)==set(expected)
        mismatch=[list(map(int,p)) for p in set(output)&set(expected) if not np.array_equal(output[p],expected[p])]
        rows=[dict(x=int(p[0]),y=int(p[1]),z=int(p[2]),size=len(pixels)) for p,pixels in sorted(output.items())]
        b.pd.DataFrame(rows).to_csv(OUT/(name+'_recovered.csv'),index=False)
        # Mark cells touching crop/acquisition edges for review, not biological acceptance.
        edge=sum(any(np.any((pixels[:,axis]==0)|(pixels[:,axis]==a.shape[axis]-1)) for axis in range(3)) for pixels in expected.values())
        result=dict(name=name,reference_seeds=len(seeds),recovered_seeds=len(output),coordinates_match=coordinate_match,
                    different_voxel_masks=mismatch,new_context_seed_observations=discoveries,edge_touching_regions=edge,blocks=traces)
        if index==0:
            single=dict(processes=1,size_min=30,size_max=30,overlap=0,axes=[2],optimization=False,verbose=False)
            for mode,settings in [('single',single),('default_blocked',proc)]:
                df=full_detector(path,settings); df.to_csv(OUT/f'{name}_{mode}_pipeline.csv',index=False)
                observed={tuple(map(int,row[:3])):int(row[3]) for row in df[['x','y','z','size']].to_numpy()}
                result[mode+'_pipeline']=dict(rows=len(df),coordinates_match=set(observed)==set(expected),
                    mismatched_sizes=sum(observed[p]!=len(expected[p]) for p in set(observed)&set(expected)),
                    duplicate_coordinates=len(df)-len(observed))
            assert result['single_pipeline']['coordinates_match'] and result['single_pipeline']['mismatched_sizes']==0
        report['crops'].append(result)
        for axis in range(3):
            plane=np.take(a,a.shape[axis]//2,axis=axis).T
            axes[index,axis].imshow(plane,cmap='gray',vmin=0,vmax=np.percentile(a,99.5),interpolation='nearest')
            axes[index,axis].set_title(f'{name}: axis {axis} midpoint')
        print(name,coordinate_match,'mask mismatches',len(mismatch),flush=True)
    fig.suptitle('Real public 3D signal: orthogonal voxel views (anisotropic, not physical aspect)')
    fig.savefig(OUT/'orthogonal-qc.png',dpi=140)
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2)); print(OUT)

if __name__=='__main__': run()
