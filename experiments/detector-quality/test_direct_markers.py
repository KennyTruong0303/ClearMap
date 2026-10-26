"""Controlled local comparison; no installed source modifications."""
import test_peak_plateaus as base
from skimage.segmentation import watershed
from ClearMap.Analysis.Measurements import shape_detection as sd

np, pd = base.np, base.pd
OUT = base.ROOT / 'test-data' / ('direct-markers-' + base.run_stamp)
original = sd.detect_shape
captured = []

def baseline(source, seeds, **kwargs):
    np.save(OUT/'baseline_seeds.npy', sd.io.as_source(seeds).array)
    return original(source, seeds, **kwargs)

def markers(shape, seeds):
    seeds = np.asarray(seeds)
    if seeds.ndim != 2 or seeds.shape[1] != len(shape):
        raise ValueError('Seed dimensions')
    if not np.all(np.isfinite(seeds)) or not np.all(seeds == np.floor(seeds)):
        raise ValueError('Seeds must be finite integers')
    if np.any(seeds < 0) or np.any(seeds >= np.asarray(shape)):
        raise ValueError('Seeds outside volume')
    if len(np.unique(seeds, axis=0)) != len(seeds):
        raise ValueError('Duplicate seed coordinates')
    result = np.zeros(shape, dtype=np.int32)
    result[tuple(seeds.astype(np.intp).T)] = np.arange(1, len(seeds)+1)
    return result

def direct(source, seeds, threshold=None, verbose=False, processes=None):
    source = sd.io.as_source(source).array
    seeds = sd.io.as_source(seeds).array
    np.save(OUT/'direct_seeds.npy', seeds)
    peaks = markers(source.shape, seeds)
    result = watershed(-source, peaks, mask=None if threshold is None else source > threshold)
    np.save(OUT/'latest_markers.npy', peaks)
    np.save(OUT/'latest_shapes.npy', result)
    return result

def run():
    OUT.mkdir(parents=True, exist_ok=False)
    tests = []
    for name, points in [('adjacent', [[2,2,0],[2,3,0]]), ('empty', np.empty((0,3))),
                         ('separate', [[1,1,0],[4,4,0]])]:
        m = markers((6,6,1), points)
        assert set(np.unique(m)) == set(range(len(points)+1))
        tests.append(name)
    for name, points in [('duplicate', [[2,2,0],[2,2,0]]), ('negative', [[-1,2,0]]),
                         ('outside', [[6,2,0]]), ('fraction', [[1.5,2,0]])]:
        try:
            markers((6,6,1), points)
        except ValueError:
            tests.append(name)
        else:
            raise AssertionError(name)
    base.Cells.detect_cells_block = base.single_thread_block
    source = base.ROOT/'test-data/neatmap/RawImage_example/RawImage_merged_25.tif'
    data = base.tifffile.imread(source)[5,0]
    report = dict(synthetic_passed=tests, runs=[], changes={}, repeatability={},
                  source_sha256=base.hashlib.sha256(source.read_bytes()).hexdigest(),
                  single_native_thread=True, plateau_correction=False,
                  runtime_sources={base.inspect.getfile(x):base.hashlib.sha256(base.Path(base.inspect.getfile(x)).read_bytes()).hexdigest() for x in [base.Cells, sd, base.md]})
    fig, axes = base.plt.subplots(2,3,figsize=(13,8),constrained_layout=True)
    for row,(region,x,y) in enumerate([('center',800,200),('right',1400,200)]):
        crop=data[y:y+256,x:x+256]
        volume=np.asfortranarray(crop.T[:,:,None]); path=OUT/(region+'.npy'); np.save(path,volume)
        tables={}
        for variant in ['baseline','direct']:
            reps=[]
            for rep in range(3):
                p=base.copy.deepcopy(base.Cells.default_cell_detection_parameter)
                p.update(illumination_correction=None,equalization=None,dog_filter=None)
                p['background_correction']['shape']=(21,21)
                p['maxima_detection'].update(shape=(11,11,1),threshold=168,h_max=None)
                p['shape_detection']['threshold']=168
                p['intensity_detection']['measure']=['source']
                sd.detect_shape=baseline if variant=='baseline' else direct
                try:
                    cells=base.Cells.detect_cells(str(path),sink=None,cell_detection_parameter=p,
                        processing_parameter=dict(processes=1,size_min=1,size_max=1,overlap=0,axes=[2],optimization=False,verbose=False))
                finally:
                    sd.detect_shape=original
                df=pd.DataFrame(cells); df['accepted']=df['size'].between(5,500)
                df.to_csv(OUT/f'{region}_{variant}_{rep}.csv',index=False); reps.append(df)
                report['runs'].append(dict(region=region,variant=variant,rep=rep,candidates=len(df),accepted=int(df.accepted.sum())))
                if variant=='direct':
                    peaks=np.load(OUT/'latest_markers.npy')
                    shapes=np.load(OUT/'latest_shapes.npy')
                    np.save(OUT/f'{region}_direct_{rep}_markers.npy',peaks)
                    np.save(OUT/f'{region}_direct_{rep}_shapes.npy',shapes)
            assert all(reps[0].equals(d) for d in reps[1:])
            report['repeatability'][region+'_'+variant]=True
            tables[variant]=reps[0]
        assert np.array_equal(np.load(OUT/'baseline_seeds.npy'),np.load(OUT/'direct_seeds.npy'))
        seed_count=len(np.load(OUT/'direct_seeds.npy'))
        joined=tables['baseline'].merge(tables['direct'],on=['x','y','z'],how='outer',suffixes=('_baseline','_direct'))
        a=joined[['x','y','z']].copy(); b=a.copy()
        for key in ['size','accepted']:
            a[key]=joined[key+'_baseline'].fillna(0 if key=='size' else False)
            b[key]=joined[key+'_direct'].fillna(0 if key=='size' else False)
        changed=a[['x','y','z']].copy()
        for key in ['size','accepted']:
            changed['baseline_'+key]=a[key]; changed['direct_'+key]=b[key]
        changed=changed[a['size']!=b['size']]; changed.to_csv(OUT/f'{region}_changed_sizes.csv',index=False)
        report['changes'][region]=dict(fixed_input_seeds=seed_count,changed_sizes=len(changed),lost=int((a.accepted & ~b.accepted).sum()),gained=int((~a.accepted & b.accepted).sum()))
        lo,hi=np.percentile(crop,[1,99.8])
        for col,variant in enumerate(['raw','baseline','direct']):
            ax=axes[row,col]; ax.imshow(crop,cmap='gray',vmin=lo,vmax=hi,interpolation='nearest')
            ax.set_title(region+' / '+variant)
            if variant!='raw':
                d=tables[variant]; d=d[d.accepted]
                ax.scatter(d.x,d.y,s=65,facecolors='none',edgecolors='lime',linewidths=0.8)
    fig.savefig(OUT/'comparison.png',dpi=160)
    report['limitations']=['Selected 2D demo crops, no biological accuracy claim','Point markers change watershed initialization and size acceptance','Plateau duplicates intentionally unchanged']
    (OUT/'report.json').write_text(base.json.dumps(report,indent=2))
    print('RESULT_DIRECTORY='+str(OUT)); print(base.json.dumps(report,indent=2))

if __name__=='__main__':
    run()
