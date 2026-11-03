"""Read-only data investigation of the remaining reviewed double detection."""
import heapq
from collections import deque
import test_direct_markers as e
b=e.base; np=b.np
root=b.ROOT/'test-data/direct-markers-20261026T030829096851Z'
out=b.ROOT/'test-data'/('double-peak-trace-'+b.run_stamp); out.mkdir()
raw=np.load(root/'right.npy')[:,:,0]
corr=b.Cells.remove_background(raw[:,:,None],shape=(21,21),form='Disk')[:,:,0]
mask=b.collapse_plateaus(corr[:,:,None],b.md.find_maxima(corr[:,:,None],shape=(11,11,1),threshold=168))[:,:,0]
seeds=np.argwhere(mask)

def widest(a,start,end):
    start=tuple(start); end=tuple(end)
    best={start:float(a[start])}; parent={}; queue=[(-best[start],start)]
    while queue:
        neg,p=heapq.heappop(queue); value=-neg
        if value<best[p]: continue
        if p==end: break
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            q=(p[0]+dx,p[1]+dy)
            if not (0<=q[0]<a.shape[0] and 0<=q[1]<a.shape[1]): continue
            v=min(value,float(a[q]))
            if v>best.get(q,-1):
                best[q]=v; parent[q]=p; heapq.heappush(queue,(-v,q))
    # Among equally strong connections, show a shortest path rather than an
    # arbitrary long route through background at the same saddle level.
    cutoff=best[end]; parent={}; seen={start}; queue=deque([start])
    while queue:
        p=queue.popleft()
        if p==end: break
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            q=(p[0]+dx,p[1]+dy)
            if 0<=q[0]<a.shape[0] and 0<=q[1]<a.shape[1] and q not in seen and a[q]>=cutoff:
                seen.add(q); parent[q]=p; queue.append(q)
    path=[end]
    while path[-1]!=start: path.append(parent[path[-1]])
    return best[end],path[::-1]

p=(149,39); q=(151,38)
near=seeds[(seeds[:,0]>=155)&(seeds[:,0]<=175)&(seeds[:,1]>=45)&(seeds[:,1]<=60)]
assert len(near)>0
lower=tuple(near[np.argmin(np.sum((near-[163,51])**2,axis=1))])
report={'scope':'2D corrected image; four-connected widest-path saddle, no detector changes','comparisons':[]}
fig,axes=b.plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
lo,hi=np.percentile(raw,[1,99.8]); extent=[139.5,175.5,64.5,24.5]
axes[0].imshow(raw[140:176,25:65].T,cmap='gray',vmin=lo,vmax=hi,extent=extent,interpolation='nearest')
axes[0].set_title('Raw: reviewed upper object and lower neighbor')
for name,pt,color in [('P',p,'cyan'),('Q',q,'orange'),('R',lower,'lime')]:
    axes[0].scatter(*pt,marker='+',color=color); axes[0].annotate(name,pt,xytext=(5,5),textcoords='offset points',color=color)
patch=corr[146:155,35:43].T
axes[1].imshow(patch,cmap='gray',vmin=0,vmax=patch.max(),extent=[145.5,154.5,42.5,34.5],interpolation='nearest')
for yy in range(35,43):
    for xx in range(146,155):
        axes[1].text(xx,yy,str(int(corr[xx,yy])),ha='center',va='center',fontsize=6,color='red')
axes[1].set_title('Corrected pixel values around P and Q')
for name,start,end,color in [('Within reviewed object',p,q,'orange'),('Upper to lower neighbor',p,lower,'green')]:
    saddle,path=widest(corr,start,end)
    values=[int(corr[t]) for t in path]; peaks=[int(corr[start]),int(corr[end])]
    report['comparisons'].append(dict(name=name,start=list(map(int,start)),end=list(map(int,end)),peaks=peaks,saddle=saddle,
        dip_below_smaller_peak=min(peaks)-saddle,path=[list(map(int,t)) for t in path],values=values))
    axes[2].plot(np.linspace(0,1,len(values)),values,'o-',label=name,color=color,markersize=3)
axes[2].axhline(168,color='gray',ls='--',label='Current threshold')
axes[2].set_title('Best connecting path: corrected signal'); axes[2].set_xlabel('Fraction along path (lengths differ)'); axes[2].legend(fontsize=7)
fig.savefig(out/'trace.png',dpi=160)
np.savetxt(out/'upper_corrected_pixels.csv',patch,delimiter=',',fmt='%d')
report['input_sha256']=b.hashlib.sha256((root/'right.npy').read_bytes()).hexdigest()
(out/'report.json').write_text(b.json.dumps(report,indent=2))
print(out); print(b.json.dumps([{k:v for k,v in c.items() if k not in ['path','values']} for c in report['comparisons']],indent=2))
