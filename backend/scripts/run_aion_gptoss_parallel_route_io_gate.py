#!/usr/bin/env python3
"""ABBA-test sequential versus parallel exact frame loading for a real route."""
from __future__ import annotations
import argparse, ctypes, fcntl, hashlib, json, os, statistics, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from backend.modules.aion_inference.gptoss_expert_frame_store import _zstd

def pct(values, q):
    values=sorted(values); return values[min(len(values)-1, int(q*len(values)+0.999999)-1)]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--layer',type=int,default=0); p.add_argument('--route',default='25,112,32,127'); p.add_argument('--repetitions',type=int,default=4); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    if a.output.exists(): raise SystemExit('refusing to overwrite evidence')
    route=[int(x) for x in a.route.split(',')]; m=json.loads(a.manifest.read_text()); root=a.manifest.parent
    addresses={}
    for region in m['regions']:
        name=region['region_name']
        prefix=f'blk.{a.layer}.ffn_'
        if not name.startswith(prefix) or '_exps.' not in name: continue
        rest=name[len(prefix):]; projection,kind=rest.split('_exps.')
        if projection not in ('gate','up','down') or kind not in ('weight','bias'): continue
        for frame in region['frames']:
            expert=frame.get('expert')
            if expert in route: addresses[(expert,projection,kind)]={**frame,'path':str(root/region['pack_relative_path'])}
    keys=[(e,pj,k) for e in route for pj in ('gate','up','down') for k in ('weight','bias')]
    if any(k not in addresses for k in keys): raise RuntimeError('route frame coverage incomplete')
    lib=_zstd()
    def load(key):
        x=addresses[key]; fd=os.open(x['path'],os.O_RDONLY)
        try:
            try: fcntl.fcntl(fd,48,1)
            except OSError: pass
            encoded=os.pread(fd,int(x['compressed_bytes']),int(x['encoded_offset']))
        finally: os.close(fd)
        if hashlib.sha256(encoded).hexdigest()!=x['compressed_sha256']: raise RuntimeError('compressed hash mismatch')
        n=int(x['raw_bytes']); out=ctypes.create_string_buffer(n); src=ctypes.create_string_buffer(encoded)
        got=lib.ZSTD_decompress(out,n,src,len(encoded))
        if lib.ZSTD_isError(got) or int(got)!=n: raise RuntimeError('decode failed')
        raw=out.raw
        if hashlib.sha256(raw).hexdigest()!=x['raw_sha256']: raise RuntimeError('raw hash mismatch')
        return key,hashlib.sha256(raw).hexdigest(),len(encoded),len(raw)
    trials=[]; expected=None; order=['sequential','parallel','parallel','sequential']
    for rep in range(a.repetitions):
        for condition in order[rep%4:]+order[:rep%4]:
            began=time.perf_counter()
            if condition=='parallel':
                with ThreadPoolExecutor(max_workers=4) as pool: rows=list(pool.map(load,keys))
            else: rows=[load(k) for k in keys]
            seconds=time.perf_counter()-began; hashes={str(k):h for k,h,_,_ in rows}
            if expected is None: expected=hashes
            trials.append({'repetition':rep,'condition':condition,'seconds':seconds,'exact':hashes==expected,
                           'compressed_bytes':sum(x[2] for x in rows),'raw_bytes':sum(x[3] for x in rows)})
    summaries={}
    for condition in ('sequential','parallel'):
        vals=[x['seconds'] for x in trials if x['condition']==condition]
        summaries[condition]={'runs':len(vals),'p50_seconds':statistics.median(vals),'p95_seconds':pct(vals,.95)}
    improvement=100*(1-summaries['parallel']['p50_seconds']/summaries['sequential']['p50_seconds'])
    report={'schema':'aion.gptoss-parallel-route-io-gate.v1','status':'PASSED' if all(x['exact'] for x in trials) else 'FAILED',
            'layer':a.layer,'route':route,'workers':4,'f_nocache_requested':True,'condition_order':order,
            'summaries':summaries,'parallel_p50_improvement_percent':improvement,'trials':trials,
            'claim_boundary':'Exact mechanism-only four-expert frame I/O and decode comparison. F_NOCACHE is requested but cannot prove absence from every OS cache. This is not a complete layer or token.'}
    report['canonical_sha256']=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:report[k] for k in ('status','summaries','parallel_p50_improvement_percent','canonical_sha256')},sort_keys=True))
if __name__=='__main__': main()
