"""Predeclared local-gradient cost; reuse the frozen challenge harnesses."""
import test_connected_seed_flood as f
import review_connected_context as c
b=f.b;np=f.np
OUT=f.ROOT/('local-cost-'+b.run_stamp)
original=f.flood
DEFINITION='Positive additive edge cost = integer physical axis distance * (1 + absolute difference of neighboring corrected intensities). No image/component maximum or fitted intensity scale. One intensity unit weights the gradient term; this methodological choice is experimental. Equal-cost front ties remain uncertain and do not propagate.'

def local(im,mask,markers,steps,ceiling_override=None):
    return original(im,mask,markers,steps,ceiling_override=ceiling_override,cost_rule='local_gradient')

def run():
    OUT.mkdir()
    (OUT/'plan.json').write_text(b.json.dumps(dict(definition=DEFINITION,scope='Same seven saved regions; same 336 orientations, connectivity, labels, repeat, ablations, synthetic controls, two depth comparisons and remote boosts. No production changes.',scale_selection='No sweep or result-based selection; gradient coefficient fixed at one.'),indent=2))
    f.flood=local;f.OUT=OUT/'regions';c.OUT=OUT/'context'
    try:
        f.run();c.run()
    finally:f.flood=original
    for path in [f.OUT/'report.json',c.OUT/'report.json']:
        report=b.json.loads(path.read_text());report['definition']=DEFINITION
        report['ceiling_override_note']='Compatibility control only; deliberately ignored by this cost rule.'
        path.write_text(b.json.dumps(report,indent=2))
    print('FINAL',OUT,flush=True)

if __name__=='__main__':run()
