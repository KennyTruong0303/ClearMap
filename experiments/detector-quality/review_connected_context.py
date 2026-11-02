"""Visual boundary review and fixed-mask depth/intensity stress tests."""
import test_connected_seed_flood as f
b=f.b;np=f.np;ROOT=f.ROOT;OUT=ROOT/('connected-context-'+b.run_stamp)

def run():
    OUT.mkdir();src=ROOT/'physical-ties-challenge-20261030T133638544441Z'
    d=np.load(src/'original_pair.npz');im=d['intensity'];mask=d['mask'];m=d['markers'];steps=np.array([18,18,40])
    trace=b.json.loads((ROOT/'canvas-trace-20261030T074555869523Z/report.json').read_text());origin=np.array(trace['objects'][1]['contexts']['8']['component_bounds_lower'])
    ref=f.flood(im,mask,m,steps);report=dict(scope='Fixed existing foreground component; no preprocessing/peak re-detection in synthetic intensity tests; no biological scoring',tests=[])
    def compare(name,result,where=None,**extra):
        where=mask if where is None else where
        row=dict(name=name,changed_labels=int(np.count_nonzero((result[0]!=ref[0])&where)),changed_ties=int(np.count_nonzero((result[1]!=ref[1])&where)),pair_membership_changes=int(np.count_nonzero((((result[0]==8)!=(ref[0]==8))|((result[0]==9)!=(ref[0]==9)))&where)),**extra)
        report['tests'].append(row);print(row,flush=True)
    # Crop the saved component at exactly the earlier source slab bounds.
    for halo in [4,6]:
        lo=1134-halo-int(origin[2]);hi=1138+halo-int(origin[2]);lo=max(0,lo);hi=min(im.shape[2],hi)
        sl=(slice(None),slice(None),slice(lo,hi));r=f.flood(im[sl],mask[sl],m[sl],steps);f.invariants(*r,m[sl],mask[sl])
        full=[np.zeros_like(x) for x in ref]
        for dest,x in zip(full,r):dest[sl]=x
        shared=np.zeros_like(mask);shared[sl]=mask[sl];core=shared.copy()
        for z in range(im.shape[2]):
            if not 1134<=origin[2]+z<1138:core[:,:,z]=False
        compare(f'halo{halo}_vs8_core',full,core,slab_global_z=[int(origin[2]+lo),int(origin[2]+hi)],ceiling=float(im[sl][mask[sl]].max()))
    p=tuple(np.argwhere(m==17)[0]);maximum=int(im[mask].max());report['boosted_seed_xyz']=(np.array(p)+origin).tolist();report['original_ceiling']=maximum
    for factor in [2,4]:
        boosted=im.copy();boosted[p]=maximum*factor
        r=f.flood(boosted,mask,m,steps);f.invariants(*r,m,mask);compare(f'boost_seed17_to_{factor}xmax',r)
        ceiling_only=f.flood(im,mask,m,steps,ceiling_override=maximum*factor)
        compare(f'ceiling_only_{factor}x',ceiling_only,equals_boosted=all(np.array_equal(x,y) for x,y in zip(r,ceiling_only)))
        np.savez_compressed(OUT/f'boost{factor}.npz',labels=r[0],tied=r[1],unreached=r[2])
    # Representative exact slices through pair and third seed; same gray window.
    zs=[1134-int(origin[2]),1135-int(origin[2])]
    fig,axes=b.plt.subplots(2,3,figsize=(12,8),constrained_layout=True)
    variants=[('Watershed',d['baseline'],np.zeros_like(mask)),('Connected flood',ref[0],ref[1]),('Boosted remote seed',np.load(OUT/'boost4.npz')['labels'],np.load(OUT/'boost4.npz')['tied'])]
    for row,z in enumerate(zs):
        for col,(name,labels,tied) in enumerate(variants):
            ax=axes[row,col];ax.imshow(im[:,:,z].T,cmap='gray',vmin=168,vmax=500,origin='lower')
            rgba=np.zeros(im.shape[:2]+(4,))
            for lab,color in [(8,[0,1,1,.5]),(9,[1,0,1,.5]),(10,[0,1,0,.5])]:rgba[labels[:,:,z]==lab]=color
            rgba[tied[:,:,z]]=[1,1,0,.8];ax.imshow(rgba.transpose(1,0,2),origin='lower')
            ax.set_title(f'{name}; Z{z+origin[2]}')
    fig.suptitle('Same corrected image behind overlays | cyan:8 magenta:9 green:10 yellow:tie\nOther seeds uncolored; synthetic boost is outside these slices. Not confirmed cell identities.')
    fig.savefig(OUT/'boundary-review.png',dpi=150);b.plt.close(fig)
    (OUT/'report.json').write_text(b.json.dumps(report,indent=2));print(OUT,flush=True)

if __name__=='__main__':run()
