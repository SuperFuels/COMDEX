"""Training-prompt-separated local affine correction probe; no injection."""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path
import time
import numpy as np
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical, digest
from backend.scripts.run_aion_gptoss_c4_coverage_queue import verify_capture

NAMES={2:'second_contribution',3:'third_contribution',4:'fourth_contribution'}


def coverage_summary(development, results):
    """Include unmatched identities in the denominator; local passes are not certificates."""
    summary={}
    for rank in NAMES:
        calls=[r for r in development if r['rank']==rank]
        fitted=[r for r in results if r['rank']==rank and 'observations' in r]
        observations=[o for r in fitted for o in r['observations']]
        supported=sum(bool(o['supported']) for o in observations)
        passing=sum(bool(o.get('local_pass',False)) for o in observations)
        usable=sum(sum(bool(o.get('local_pass',False)) for o in r['observations'])
                   for r in fitted if r['status']=='LOCAL_CANDIDATE_REQUIRES_UNTOUCHED_VALIDATION')
        summary[str(rank)]={
            'all_development_calls':len(calls),
            'calls_without_fitted_identity':len(calls)-len(observations),
            'supported_calls':supported,'local_passing_calls':passing,
            'candidate_region_passing_calls':usable,
            'candidate_traffic_share':usable/len(calls) if calls else None,
            'certified_traffic_share':None}
    return summary


def fit_local(x, y, gates):
    """Expert-specific affine kernel ridge, fixed regularization and F32 storage."""
    x=np.asarray(x,dtype=np.float64); y=np.asarray(y,dtype=np.float64)
    gates=np.asarray(gates,dtype=np.float64)
    if x.ndim!=2 or y.shape!=x.shape or gates.shape!=(len(x),) or len(x)<4:
        raise ValueError('at least four aligned fitting targets required')
    if not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isfinite(gates).all() or np.any(gates<=0):
        raise ValueError('invalid fitting values')
    center=x.mean(axis=0)
    scale=max(float(np.linalg.norm(x-center,axis=1).mean()),1e-12)
    anchors=(x-center)/scale
    kernel=anchors@anchors.T+1
    coefficients=np.linalg.solve(kernel+np.eye(len(x))*1e-3,y/gates[:,None])
    return {name:np.asarray(value,dtype='<f4') for name,value in
            {'center':center,'scale':scale,'anchors':anchors,'coefficients':coefficients,
             'unit_anchors':x/np.maximum(np.linalg.norm(x,axis=1,keepdims=True),1e-30)}.items()}


def predict(model, activation, gate):
    unit=activation/np.float32(max(float(np.linalg.norm(activation)),1e-30))
    similarity=float(np.max(model['unit_anchors']@unit))
    if similarity<.80:
        return None,similarity
    z=(activation-model['center'])/model['scale']
    weights=model['anchors']@z+np.float32(1)
    return (weights@model['coefficients'])*np.float32(gate),similarity


def load_job(job, corpus, layer, include_prefill=False):
    row=next((r for r in corpus['rows'] if r['capture_id']==job.name and r['split']=='training'),None)
    if row is None:
        raise RuntimeError('only declared training prompts may be used')
    seal=json.loads((job/'COMPLETE_VERIFIED.json').read_text()); body=dict(seal)
    if body.pop('canonical_sha256',None)!=canonical(body) or seal['corpus_canonical_sha256']!=corpus['canonical_sha256']:
        raise RuntimeError('completion hash mismatch')
    receipt=json.loads((job/'teacher.json').read_text())
    verify_capture(receipt,job/'captures',len(row['capture_positions'])*36)
    if seal['teacher_canonical_sha256']!=receipt['canonical_sha256']:
        raise RuntimeError('completion teacher mismatch')
    files=[{'name':p.name,'sha256':digest(p),'bytes':p.stat().st_size}
           for p in sorted((job/'captures').iterdir()) if p.is_file()]
    if files!=seal['capture_files']:
        raise RuntimeError('sealed file tree differs')
    rows=[]
    for path in sorted((job/'captures').glob(f'position-*-layer-{layer}.json')):
        m=json.loads(path.read_text())
        if not include_prefill and m['position']<row['prompt_token_count']:
            continue
        stem=path.with_suffix('')
        x=np.fromfile(f'{stem}-router.bin',dtype='<f4')
        output=np.fromfile(f'{stem}-output.bin',dtype='<f4')
        for rank,name in NAMES.items():
            if f'{name}_sha256' not in m:
                continue
            target=np.fromfile(f'{stem}-{name}.bin',dtype='<f4')
            rows.append({'rank':rank,'expert':m['route'][rank-1], 'position':m['position'],
                         'x':x,'target':target,'gate':m['native_gates_f32'][rank-1],
                         'output_norm':max(float(np.linalg.norm(output.astype(np.float64))),1e-30)})
    return row,seal,rows


def chronological_sanity(job,corpus_path,destination,layer):
    """Cheap real-data smoke: prefill fit vs continuation, same prompt.

    Temporal positions are separate, but this is NOT independent-prompt transfer.
    No certificate, development selection or runtime substitution is permitted.
    """
    corpus=json.loads(corpus_path.read_text());body=dict(corpus)
    if body.pop('canonical_sha256',None)!=canonical(body):
        raise RuntimeError('corpus hash mismatch')
    row,seal,data=load_job(job,corpus,layer,include_prefill=True)
    groups=defaultdict(list)
    for item in data:
        groups[(item['rank'],item['expert'])].append(item)
    destination.mkdir(parents=True,exist_ok=False)
    results=[]
    for key,items in sorted(groups.items()):
        fitting=[r for r in items if r['position']<row['prompt_token_count']]
        testing=[r for r in items if r['position']>=row['prompt_token_count']]
        if len(fitting)<4 or not testing:
            continue
        model=fit_local([r['x'] for r in fitting],[r['target'] for r in fitting],[r['gate'] for r in fitting])
        cartridge=destination/f'rank-{key[0]}-expert-{key[1]}.npz'
        with cartridge.open('xb') as handle:
            np.savez(handle,**model)
        observations=[]
        for test in testing:
            prediction,similarity=predict(model,test['x'],test['gate'])
            obs={'position':test['position'],'supported':prediction is not None,'similarity':similarity}
            if prediction is not None:
                error=float(np.linalg.norm(prediction.astype(np.float64)-test['target'])/test['output_norm'])
                drop=float(np.linalg.norm(test['target'].astype(np.float64))/test['output_norm'])
                obs.update(relative_l2=error,drop_relative_l2=drop,local_pass=error<=.02 and error<drop)
            observations.append(obs)
        results.append({'rank':key[0],'expert':key[1],'fitting_positions':[r['position'] for r in fitting],
                        'cartridge_sha256':digest(cartridge),'resident_bytes':sum(v.nbytes for v in model.values()),
                        'observations':observations})
    report={'schema':'aion.ranked-correction-chronological-sanity.v1','status':'SANITY_ONLY_NOT_CERTIFIED',
            'layer':layer,'completion_sha256':seal['canonical_sha256'],'results':results,
            'claim_boundary':'Same-prompt prefill-to-continuation sanity only; temporally dependent data, not cross-family or untouched validation. No accuracy certificate, cost ratio or speed promotion.'}
    report['canonical_sha256']=canonical(report)
    with (destination/'report.json').open('x') as handle:
        json.dump(report,handle,indent=2,sort_keys=True);handle.write('\n')
    return report


def gate(training_job, development_job, corpus_path, destination, layer=12):
    corpus=json.loads(corpus_path.read_text()); body=dict(corpus)
    if body.pop('canonical_sha256',None)!=canonical(body):
        raise RuntimeError('corpus hash mismatch')
    tr,ts,training=load_job(training_job,corpus,layer)
    dr,ds,development=load_job(development_job,corpus,layer)
    if tr['capture_id']==dr['capture_id'] or tr['family']==dr['family']:
        raise RuntimeError('different fitting and development prompt families required')
    grouped=defaultdict(list)
    for row in training:
        grouped[(row['rank'],row['expert'])].append(row)
    destination.mkdir(parents=True,exist_ok=False)
    results=[]
    for key,rows in sorted(grouped.items()):
        tests=[r for r in development if (r['rank'],r['expert'])==key]
        if len(rows)<4 or not tests:
            results.append({'rank':key[0],'expert':key[1],'training_calls':len(rows),
                            'development_calls':len(tests),'status':'INSUFFICIENT_SUPPORT'})
            continue
        rows=rows[:32]
        model=fit_local([r['x'] for r in rows],[r['target'] for r in rows],[r['gate'] for r in rows])
        path=destination/f'rank-{key[0]}-expert-{key[1]}.npz'
        with path.open('xb') as handle:
            np.savez(handle,**model)
        observations=[]
        for row in tests:
            start=time.perf_counter_ns()
            prediction,similarity=predict(model,row['x'],row['gate'])
            ms=(time.perf_counter_ns()-start)/1e6
            obs={'position':row['position'],'similarity':similarity,'supported':prediction is not None}
            if prediction is not None:
                error=float(np.linalg.norm(prediction.astype(np.float64)-row['target'])/row['output_norm'])
                drop=float(np.linalg.norm(row['target'].astype(np.float64))/row['output_norm'])
                obs.update(relative_l2=error,drop_relative_l2=drop,correction_ms=ms,
                           local_pass=error<=.02 and error<drop)
            observations.append(obs)
        supported=[o for o in observations if o['supported']]
        payload=sum(v.nbytes for v in model.values())
        results.append({'rank':key[0],'expert':key[1],'training_calls':len(rows),'development_calls':len(tests),
                        'cartridge_sha256':digest(path),'resident_bytes':payload,
                        'storage_cost_pass':payload<.25*13.25*1024**2,
                        'status':'LOCAL_CANDIDATE_REQUIRES_UNTOUCHED_VALIDATION' if supported and all(o['local_pass'] for o in supported) and payload<.25*13.25*1024**2 else 'NOT_CERTIFIED',
                        'observations':observations})
    report={'schema':'aion.ranked-local-correction-probe.v1','layer':layer,
            'training_completion_sha256':ts['canonical_sha256'],'development_completion_sha256':ds['canonical_sha256'],
            'training_prompt':tr['capture_id'],'development_prompt':dr['capture_id'],
            'policy':{'minimum_fit_calls':4,'maximum_fit_calls':32,'regularization':.001,'minimum_cosine':.80,'maximum_local_error':.02},
            'results':results,'coverage':coverage_summary(development,results),
            'claim_boundary':'Training/development probe only. No sealed holdout, adaptive-state certificate, compute-cost ratio, downstream token validation or speed gain. Single-call timing during active teacher load is diagnostic only. Rank-specific teacher targets cannot certify changed active-count execution.'}
    report['canonical_sha256']=canonical(report)
    with (destination/'report.json').open('x') as handle:
        json.dump(report,handle,indent=2,sort_keys=True);handle.write('\n')
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--training-job',type=Path,required=True)
    p.add_argument('--development-job',type=Path,required=True);p.add_argument('--corpus',type=Path,required=True)
    p.add_argument('--output-directory',type=Path,required=True);a=p.parse_args()
    print(gate(a.training_job,a.development_job,a.corpus,a.output_directory)['canonical_sha256'])

if __name__=='__main__':
    main()
