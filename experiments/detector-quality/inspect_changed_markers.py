"""Reconstruct and verify segmentation close-ups from the saved experiment."""
import test_direct_markers as exp
b=exp.base
np=b.np
root=b.ROOT/'test-data/direct-markers-20261026T030829096851Z'
out=b.ROOT/'test-data'/('marker-closeups-'+b.run_stamp)
out.mkdir()
records=[]
fig,axes=b.plt.subplots(3,4,figsize=(13,10),constrained_layout=True)
for row,(region,x,y) in enumerate([('center',15,190),('center',136,142),('right',190,170)]):
    raw=np.load(root/(region+'.npy'))
    corrected=b.Cells.remove_background(raw,shape=(21,21),form='Disk')
    mask=b.md.find_maxima(corrected,shape=(11,11,1),threshold=168)
    seeds=np.argwhere(mask)
    label=int(np.flatnonzero(np.all(seeds==[x,y,0],axis=1))[0])+1
    baseline=exp.original(corrected,seeds,threshold=168,processes=1)
    direct=np.load(root/f'{region}_direct_0_shapes.npy')
    # Independently reconstruct direct segmentation and compare saved output.
    from skimage.segmentation import watershed
    assert np.array_equal(direct,watershed(-corrected,exp.markers(raw.shape,seeds),mask=corrected>168))
    sizes=[int((s==label).sum()) for s in [baseline,direct]]
    oldmarkers=exp.sd.vox.voxelize(seeds,shape=raw.shape,weights=np.arange(1,len(seeds)+1),processes=1).array
    print('CASE',chr(65+row),'seed ID',label,'original marker at seed',int(oldmarkers[x,y,0]))
    for point in np.argwhere((baseline==label)!=(direct==label)):
        contributors=np.flatnonzero(np.sum((seeds-point)**2,axis=1)<=1)+1
        print('changed pixel',point.tolist(),'marker',int(oldmarkers[tuple(point)]),'nearby seed IDs',contributors.tolist())
    for variant,size in zip(['baseline','direct'],sizes):
        table=b.pd.read_csv(root/f'{region}_{variant}_0.csv')
        match=table[(table.x==x)&(table.y==y)&(table.z==0)]
        assert len(match)==1 and int(match.iloc[0]['size'])==size
    sl=(slice(x-10,x+11),slice(y-10,y+11),0)
    raw_patch=raw[sl].T; corr_patch=corrected[sl].T
    lo,hi=np.percentile(raw[:,:,0],[1,99.8])
    extent=[x-10.5,x+10.5,y+10.5,y-10.5]
    for col,title in enumerate(['Raw signal','Background corrected','Original markers','Direct markers']):
        ax=axes[row,col]
        ax.imshow(corr_patch if col==1 else raw_patch,cmap='gray',
                  vmin=0 if col==1 else lo,vmax=max(168*2,float(corr_patch.max())) if col==1 else hi,
                  extent=extent,interpolation='nearest')
        if col==1:
            active=(corrected[sl]>168).T
            ax.contour(np.arange(x-10,x+11),np.arange(y-10,y+11),active,levels=[.5],colors=['cyan'],linewidths=.7)
        if col>=2:
            s=[baseline,direct][col-2]
            overlay=np.zeros((21,21,4)); overlay[(s[sl]==label).T]=[1,.2,.1,.65]
            ax.imshow(overlay,extent=extent,interpolation='nearest')
            title+=f'\n{sizes[col-2]} pixels: '+('accepted' if 5<=sizes[col-2]<=500 else 'excluded')
            outside=sizes[col-2]-int((s[sl]==label).sum())
            if outside: title+=f'\n({outside} pixels elsewhere in crop!)'
        # Crosshair remains outside the central pixels.
        ax.plot([x-4,x-2],[y,y],color='yellow',lw=1)
        ax.plot([x+2,x+4],[y,y],color='yellow',lw=1)
        ax.set_title(title,fontsize=10)
        ax.set_xticks([x-10,x,x+10]); ax.set_yticks([y-10,y,y+10])
        if col==0: ax.set_ylabel(f'{chr(65+row)}: {region} ({x}, {y})')
    records.append(dict(case=chr(65+row),region=region,x=x,y=y,seed_label=label,
                        baseline_size=sizes[0],direct_size=sizes[1],
                        baseline_pixels=np.argwhere(baseline==label).tolist(),
                        direct_pixels=np.argwhere(direct==label).tolist(),
                        corrected_peak=int(corrected[x,y,0])))
    np.save(out/f'{region}_{x}_{y}_baseline.npy',baseline==label)
    np.save(out/f'{region}_{x}_{y}_direct.npy',direct==label)
fig.suptitle('Same raw contrast across methods; red = pixels assigned to this seed\nCyan = corrected signal >168; yellow ticks point to the seed; coordinates are crop pixels',fontsize=11)
fig.savefig(out/'three-objects.png',dpi=160)
(out/'report.json').write_text(b.json.dumps(records,indent=2))
print(out); print(b.json.dumps(records,indent=2))
