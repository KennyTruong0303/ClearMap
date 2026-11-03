"""Fixed-input test of direct markers with and without connected-plateau collapse."""
import test_direct_markers as e
from skimage.segmentation import watershed
b=e.base; np=b.np
root=b.ROOT/'test-data/direct-markers-20261026T030829096851Z'
out=b.ROOT/'test-data'/('combined-markers-'+b.run_stamp); out.mkdir()
cases=[('center',113,43,'Reviewed object 1'),('center',33,138,'Reviewed object 2'),
       ('center',98,113,'Reviewed object 3'),('right',150,39,'Reviewed upper object'),
       ('right',190,170,'C: one object')]
results={}; report={'parameters':{'threshold':168,'maxima':[11,11,1],'background':[21,21],'size':[5,500]},'crops':{},'cases':[],
 'limitations':['Selected 2D tuning cases; no independent accuracy estimate','ROI counts are local diagnostics, not object truth','A and B remain uncertain and are not tuning targets']}
for region in ['center','right']:
    raw=np.load(root/(region+'.npy')); corrected=b.Cells.remove_background(raw,shape=(21,21),form='Disk')
    mask=b.md.find_maxima(corrected,shape=(11,11,1),threshold=168)
    report['crops'][region]={}
    for variant,m in [('direct',mask),('combined',b.collapse_plateaus(corrected,mask))]:
        seeds=np.argwhere(m); markers=e.markers(raw.shape,seeds)
        shapes=watershed(-corrected,markers,mask=corrected>168)
        for repeat in range(2):
            assert np.array_equal(shapes,watershed(-corrected,e.markers(raw.shape,seeds),mask=corrected>168))
        sizes=np.bincount(shapes.ravel(),minlength=len(seeds)+1)[1:]
        if variant=='direct': assert np.array_equal(shapes,np.load(root/f'{region}_direct_0_shapes.npy'))
        table=b.pd.DataFrame(seeds,columns=['x','y','z']); table['size']=sizes; table['accepted']=table['size'].between(5,500)
        table.to_csv(out/f'{region}_{variant}.csv',index=False)
        np.save(out/f'{region}_{variant}_shapes.npy',shapes)
        results[region,variant]=(raw,shapes,table)
        report['crops'][region][variant]={'seeds':len(seeds),'accepted':int(table.accepted.sum()),'three_shape_runs_identical':True}
fig,axes=b.plt.subplots(len(cases),3,figsize=(10,15),constrained_layout=True)
for row,(region,x,y,title) in enumerate(cases):
    raw=results[region,'direct'][0]; lo,hi=np.percentile(raw[:,:,0],[1,99.8])
    r=9; extent=[x-r-.5,x+r+.5,y+r+.5,y-r-.5]; sl=(slice(x-r,x+r+1),slice(y-r,y+r+1),0)
    case={'title':title,'region':region,'crop_xy':[x,y],'variants':{}}
    for col,variant in enumerate(['raw','direct','combined']):
        ax=axes[row,col]; ax.imshow(raw[sl].T,cmap='gray',vmin=lo,vmax=hi,extent=extent,interpolation='nearest')
        if col:
            _,shapes,table=results[region,variant]
            local=table[table.x.between(x-r,x+r)&table.y.between(y-r,y+r)]
            # Color every foreground label, with reproducible distinct colors.
            labels=shapes[sl].T; rgba=np.zeros(labels.shape+(4,))
            for label in np.unique(labels):
                if label:
                    rgba[labels==label]=b.plt.get_cmap('tab20')(int(label)%20); rgba[labels==label,3]=.35
            ax.imshow(rgba,extent=extent,interpolation='nearest')
            for _,item in local.iterrows():
                ax.scatter(item.x,item.y,s=35,marker='+',color='lime' if item.accepted else 'yellow')
                ax.annotate(str(int(item['size'])),(item.x,item.y),xytext=(4,4),textcoords='offset points',color='white',fontsize=8)
            ax.set_title(f'{variant}: {len(local)} seeds / {int(local.accepted.sum())} accepted',fontsize=10)
            case['variants'][variant]=local.to_dict(orient='records')
        else: ax.set_title(title,fontsize=10)
        ax.set_xticks([x-r,x,x+r]); ax.set_yticks([y-r,y,y+r])
    report['cases'].append(case)
fig.suptitle('Fixed thresholds: direct markers vs direct markers + connected plateau correction\nColors show regions; + marks seeds (green accepted, yellow excluded); numbers are region sizes',fontsize=10)
fig.savefig(out/'reviewed-objects.png',dpi=150)
report['input_sha256']={region:b.hashlib.sha256((root/(region+'.npy')).read_bytes()).hexdigest() for region in ['center','right']}
(out/'report.json').write_text(b.json.dumps(report,indent=2))
print(out); print(b.json.dumps(report,indent=2))
