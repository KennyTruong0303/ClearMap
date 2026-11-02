"""Frozen original detector context challenge; not biological accuracy scoring."""
import test_peak_plateaus as b
np=b.np
ROOT=b.ROOT/'test-data/canvas-audit'
OUT=b.ROOT/'test-data'/('canvas-context-'+b.run_stamp)
CORE_LO=np.array([4422,3218,1134]); CORE_HI=np.array([4682,3478,1138])

def run():
    OUT.mkdir()
    a=np.load(ROOT/'expanded-zyx.npy').transpose(2,1,0)
    origin=np.array([4382,3178,1130])
    p=b.copy.deepcopy(b.Cells.default_cell_detection_parameter)
    p.update(illumination_correction=None,equalization=None,dog_filter=None)
    p['background_correction']['shape']=(21,21)
    p['maxima_detection'].update(shape=(11,11,1),threshold=168,h_max=None)
    p['shape_detection']['threshold']=168
    p['intensity_detection']['measure']=['source']
    plan=dict(core_lower_xyz=CORE_LO.tolist(),core_upper_xyz=CORE_HI.tolist(),
       ownership='half-open center coordinates; same core for every run',
       contexts=[[10,1],[20,2],[40,4],[40,1],[40,2],[40,3]], parameters=p,
       scope='Original installed ClearMap algorithms, frozen earlier experimental configuration; not stock default configuration or biological accuracy. Single native thread only; no plateau/direct-marker/component fixes.',
       stopping_rule='Require identical core coordinate multiset and per-coordinate size/intensity across context increases and largest-context repeat. Agreement is bounded empirical evidence only.')
    (OUT/'plan.json').write_text(b.json.dumps(plan,indent=2,default=str))
    b.Cells.detect_cells_block=b.single_thread_block
    tables={}
    try:
      for name,xy,z in [('small',10,1),('medium',20,2),('large',40,4),('large_repeat',40,4),('xy40_z1',40,1),('xy40_z2',40,2),('xy40_z3',40,3)]:
        lo=CORE_LO-[xy,xy,z];hi=CORE_HI+[xy,xy,z]
        assert np.all(lo>=origin) and np.all(hi<=origin+a.shape)
        sl=tuple(slice(int(l),int(h)) for l,h in zip(lo-origin,hi-origin))
        vol=np.asfortranarray(a[sl]);path=OUT/(name+'.npy');np.save(path,vol)
        n=vol.shape[2]
        result=b.Cells.detect_cells(str(path),sink=None,cell_detection_parameter=b.copy.deepcopy(p),
          processing_parameter=dict(processes=1,size_min=n,size_max=n,overlap=0,axes=[2],optimization=False,verbose=False))
        df=b.pd.DataFrame(result);df[['x','y','z']]+=lo
        core=df.loc[np.all((df[['x','y','z']].to_numpy()>=CORE_LO)&(df[['x','y','z']].to_numpy()<CORE_HI),axis=1)].sort_values(['x','y','z']).reset_index(drop=True)
        core.to_csv(OUT/(name+'_core.csv'),index=False);tables[name]=core
        print(name,'core candidates',len(core),flush=True)
    finally:b.Cells.detect_cells_block=b.ORIGINAL_BLOCK
    comparisons=[]
    for left,right in [('small','medium'),('medium','large'),('large','large_repeat'),('xy40_z1','xy40_z2'),('xy40_z2','xy40_z3'),('xy40_z3','large')]:
      l=tables[left];r=tables[right];cols=['x','y','z']
      coords=l[cols].equals(r[cols]); comparison=dict(left=left,right=right,coordinates_equal=coords,all_fields_equal=l.equals(r))
      joined=l.merge(r,on=cols,suffixes=('_left','_right'))
      comparison['common_coordinates']=len(joined)
      comparison['common_size_changes']=int((joined['size_left']!=joined['size_right']).sum())
      comparison['accepted_size_5_500']=[int(t['size'].between(5,500).sum()) for t in (l,r)]
      if coords:
        comparison['changed_fields']={c:int((l[c]!=r[c]).sum()) for c in l.columns if c not in cols}
      comparisons.append(comparison)
    report=dict(comparisons=comparisons,passed=all(c['all_fields_equal'] for c in comparisons))
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2));print(OUT,report,flush=True)
if __name__=='__main__':run()
