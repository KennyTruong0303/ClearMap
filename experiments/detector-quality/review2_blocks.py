"""Controlled block/shape test with known synthetic seeds, configured overlaps."""
import validate_component_segmentation as v
b=v.b; np=b.np; e=v.e
out=b.ROOT/'test-data'/('review2-blocks-'+b.run_stamp)

def fixed_maxima(source,**kwargs):
    return np.asarray(source)==1000

def shape(source,seeds,threshold=None,verbose=False,processes=None):
    a=e.sd.io.as_source(source).array; seeds=e.sd.io.as_source(seeds).array
    return v.segment(-a.astype(float),e.markers(a.shape,seeds),a>threshold)

def keep_halo_block(source,parameter=b.Cells.default_cell_detection_parameter,n_threads=None):
    p=b.copy.deepcopy(parameter); p['maxima_detection']['valid']=False
    result=b.ORIGINAL_BLOCK(source,parameter=p,n_threads=1)
    lo=np.array(source.lower)+source.valid.lower; hi=np.array(source.lower)+source.valid.upper
    take=np.all((result[0]>=lo)&(result[0]<hi),axis=1)
    return tuple(item[take] for item in result)

def run():
    out.mkdir(); configs=[('machine_cfg',10,16,5),('api_default',50,100,32)]
    report={'scope':'Known synthetic peak masks, no background correction, threshold 168. Actual ClearMap blocking and cell measurement; not validation of upstream peak finding/preprocessing. One worker/native thread; configured block sizes and overlap unchanged.', 'cases':[]}
    original=(b.Cells.detect_cells_block,b.md.find_maxima,e.sd.detect_shape)
    b.Cells.detect_cells_block=b.single_thread_block; b.md.find_maxima=fixed_maxima; e.sd.detect_shape=shape
    try:
        for config,minimum,maximum,overlap in configs:
            probe=np.zeros((25,25,240),dtype=np.uint16)
            processing=dict(processes=1,size_min=minimum,size_max=maximum,overlap=overlap,axes=[2],optimization=True,optimization_fix='all',verbose=False)
            blocks=b.Cells.bp.split_into_blocks(b.Cells.clearmap_io.as_source(probe),**processing)
            chosen=blocks[len(blocks)//2]
            # valid.lower is block-local, not a global split coordinate.
            boundary=int(chosen.lower[2]+chosen.valid.lower[2])
            report[config+'_blocks']=[dict(lower=list(map(int,k.lower)),upper=list(map(int,k.upper)),valid_global_lower=(np.array(k.lower)+k.valid.lower).astype(int).tolist(),valid_global_upper=(np.array(k.lower)+k.valid.upper).astype(int).tolist()) for k in blocks]
            for kind,radius,offset in [('compact_before',1,-1),('compact_at',1,0),('compact_after',1,1),('extended',6 if overlap==5 else 25,0),('competing_across',4,0)]:
                a=np.zeros_like(probe); grid=np.indices(a.shape)
                centers=[(12,12,boundary+offset)] if kind!='competing_across' else [(12,12,boundary-2),(12,12,boundary+2)]
                for center in centers:
                    d=((grid[0]-center[0])/3)**2+((grid[1]-center[1])/3)**2+((grid[2]-center[2])/radius)**2
                    intensity=np.where(d<=1,1000-800*d,0).astype(np.uint16)
                    a=np.maximum(a,intensity)
                path=out/f'{config}_{kind}.npy'; np.save(path,np.asfortranarray(a))
                tables={}
                modes=[('single',dict(processes=1,size_min=240,size_max=240,overlap=0,axes=[2],optimization=False,verbose=False)),('blocked',processing)]
                if kind=='competing_across': modes.append(('keep_halo_control',processing))
                for mode,proc in modes:
                    b.Cells.detect_cells_block=keep_halo_block if mode=='keep_halo_control' else b.single_thread_block
                    p=b.copy.deepcopy(b.Cells.default_cell_detection_parameter)
                    p.update(illumination_correction=None,background_correction=None,equalization=None,dog_filter=None)
                    p['maxima_detection'].update(h_max=None,threshold=168,valid=True)
                    p['shape_detection']['threshold']=168; p['intensity_detection']['measure']=['source']
                    cells=b.Cells.detect_cells(str(path),sink=None,cell_detection_parameter=p,processing_parameter=proc)
                    df=b.pd.DataFrame(cells).sort_values(['x','y','z']).reset_index(drop=True)
                    df.to_csv(out/f'{config}_{kind}_{mode}.csv',index=False); tables[mode]=df
                report['cases'].append(dict(config=config,kind=kind,boundary=boundary,overlap=overlap,
                    single=tables['single'].to_dict(orient='records'),blocked=tables['blocked'].to_dict(orient='records'),
                    all_measurements_equal=tables['single'].equals(tables['blocked']),
                    coordinates_equal=np.array_equal(tables['single'][['x','y','z']],tables['blocked'][['x','y','z']])))
                if 'keep_halo_control' in tables:
                    report['cases'][-1]['keep_halo_control']=tables['keep_halo_control'].to_dict(orient='records')
                    report['cases'][-1]['keep_halo_matches_single']=tables['single'].equals(tables['keep_halo_control'])
    finally:
        b.Cells.detect_cells_block,b.md.find_maxima,e.sd.detect_shape=original
    (out/'report.json').write_text(b.json.dumps(report,indent=2)); print(out); print(b.json.dumps(report['cases'],indent=2))

if __name__=='__main__': run()
