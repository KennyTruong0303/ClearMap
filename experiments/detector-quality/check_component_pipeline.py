"""Check experimental component segmentation through ClearMap's full detector."""
import validate_component_segmentation as v
b=v.b; np=v.np; e=v.e
from pathlib import Path
out=b.ROOT/'test-data'/('component-pipeline-'+b.run_stamp); out.mkdir()
reference=b.ROOT/'test-data/component-validation-20261026T112815693824Z'

def detect(source,seeds,threshold=None,verbose=False,processes=None):
    image=e.sd.io.as_source(source).array; coords=e.sd.io.as_source(seeds).array
    mask=np.ones(image.shape,dtype=bool) if threshold is None else image>threshold
    return v.segment(-image.astype(float),e.markers(image.shape,coords),mask)

orig_block=b.Cells.detect_cells_block; orig_max=b.md.find_maxima; orig_shape=e.sd.detect_shape
report=[]
try:
    b.Cells.detect_cells_block=b.single_thread_block
    b.md.find_maxima=b.experimental_maxima
    e.sd.detect_shape=detect
    data=b.tifffile.imread(b.ROOT/'test-data/neatmap/RawImage_example/RawImage_merged_26.tif')[5,0]
    for x,y in [(800,200),(1400,200),(1400,450)]:
        name=f'image26_x{x}_y{y}'; path=out/(name+'.npy')
        np.save(path,np.asfortranarray(data[y:y+256,x:x+256].T[:,:,None]))
        p=b.copy.deepcopy(b.Cells.default_cell_detection_parameter)
        p.update(illumination_correction=None,equalization=None,dog_filter=None)
        p['background_correction']['shape']=(21,21)
        p['maxima_detection'].update(shape=(11,11,1),threshold=168,h_max=None)
        p['shape_detection']['threshold']=168; p['intensity_detection']['measure']=['source']
        tables=[]
        for rep in range(2):
            cells=b.Cells.detect_cells(str(path),sink=None,cell_detection_parameter=p,
                processing_parameter=dict(processes=1,size_min=1,size_max=1,overlap=0,axes=[2],optimization=False,verbose=False))
            df=b.pd.DataFrame(cells).sort_values(['x','y','z']).reset_index(drop=True)
            df.to_csv(out/f'{name}_{rep}.csv',index=False); tables.append(df)
        assert tables[0].equals(tables[1])
        expected=b.pd.read_csv(reference/(name+'.csv'))
        expected=expected[expected.component_size>0].sort_values(['x','y','z']).reset_index(drop=True)
        assert np.array_equal(tables[0][['x','y','z','size']].to_numpy(),expected[['x','y','z','component_size']].to_numpy())
        report.append(dict(crop=name,rows=len(tables[0]),accepted=int(tables[0]['size'].between(5,500).sum()),
                           two_full_runs_identical=True,all_coordinates_and_sizes_match_stage=True))
finally:
    b.Cells.detect_cells_block=orig_block; b.md.find_maxima=orig_max; e.sd.detect_shape=orig_shape
(out/'report.json').write_text(b.json.dumps(report,indent=2)); print(out); print(b.json.dumps(report,indent=2))
