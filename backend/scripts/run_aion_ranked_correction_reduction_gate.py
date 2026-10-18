"""Real packed E2/E3/E4 reduction audit from existing read-only local L2."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore,GptOssPersistentL2ExpertFrameStore,ctypes_component_pointer_array
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical,digest,load,WIDTH


def read_cached(store,root,layer,expert):
    path=root/digest(store.manifest_path)/f'layer-{layer:02d}-expert-{expert:03d}.aionraw'
    payload=path.read_bytes()
    fmt=GptOssPersistentL2ExpertFrameStore._HEADER
    magic,*lengths=fmt.unpack_from(payload)
    if magic!=GptOssPersistentL2ExpertFrameStore._MAGIC or fmt.size+sum(lengths)!=len(payload):
        raise RuntimeError('invalid local cached frame')
    cursor=fmt.size;result={}
    for (projection,kind),length in zip(GptOssPersistentL2ExpertFrameStore._ORDER,lengths,strict=True):
        raw=payload[cursor:cursor+length];cursor+=length
        address=store._addresses[(layer,expert,projection,kind)]
        if len(raw)!=int(address['raw_bytes']) or hashlib.sha256(raw).hexdigest()!=address['raw_sha256']:
            raise RuntimeError('cached component differs from warehouse manifest')
        result.setdefault(projection,{})[kind]=raw
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--l2-root',type=Path,required=True);p.add_argument('--capture-stem',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():
        raise SystemExit('refusing to overwrite evidence')
    meta,x,ffn,frozen=load(a.capture_stem)
    store=GptOssExpertFrameStore(a.manifest,64*1024**2)
    values=[read_cached(store,a.l2_root,meta['layer'],e) for e in meta['route']]
    blobs=[v[projection][kind] for v in values for projection in ('gate','up','down') for kind in ('weight','bias')]
    refs,pointers=ctypes_component_pointer_array(blobs)
    gates=np.asarray(meta['native_gates_f32'],dtype=np.float32)
    source=Path(__file__).parents[1]/'modules/aion_inference/native/gptoss_persistent_moe_library.cpp'
    fp=ctypes.POINTER(ctypes.c_float);vp=ctypes.POINTER(ctypes.c_void_p);dp=ctypes.POINTER(ctypes.c_double)
    ptr=lambda array:array.ctypes.data_as(fp)
    results=[]
    with tempfile.TemporaryDirectory(prefix='aion-ranked-order-') as directory:
        library_path=Path(directory)/'moe.dylib'
        subprocess.run(['clang++','-std=c++17','-O3','-dynamiclib','-I/opt/homebrew/include',str(source),'-L/opt/homebrew/lib','-lggml','-lggml-base','-ldl','-o',str(library_path)],check=True)
        library=ctypes.CDLL(str(library_path))
        active=library.aion_gptoss_moe_finish_active
        active.argtypes=[fp,fp,vp,fp,ctypes.c_int,fp,ctypes.c_int,dp]
        one=library.aion_gptoss_one_expert_contribution_batch
        one.argtypes=[fp,vp,fp,ctypes.c_int,fp,ctypes.c_int,dp]
        corrected=library.aion_gptoss_moe_finish_ranked_correction
        corrected.argtypes=[fp,fp,vp,fp,ctypes.c_int,fp,fp,ctypes.c_int,dp]
        for n in (2,3,4):
            reference=np.empty(WIDTH,dtype=np.float32);correction=np.empty_like(reference);candidate=np.empty_like(reference)
            tailrefs,tailptrs=ctypes_component_pointer_array(blobs[(n-1)*6:n*6])
            ms=ctypes.c_double()
            calls=[lambda:active(ptr(ffn),ptr(x),pointers,ptr(gates),n,ptr(reference),1,ctypes.byref(ms)),
                   lambda:one(ptr(x),tailptrs,ptr(gates[n-1:n]),1,ptr(correction),1,ctypes.byref(ms)),
                   lambda:corrected(ptr(ffn),ptr(x),pointers,ptr(gates),n-1,ptr(correction),ptr(candidate),1,ctypes.byref(ms))]
            for call in calls:
                status=call()
                if status:
                    raise RuntimeError(f'native reduction failed: {status}')
            results.append({'active_experts':n,'retained_experts':n-1,
                            'differing_output_elements':int(np.count_nonzero(reference!=candidate)),
                            'bitwise_equal':reference.tobytes()==candidate.tobytes()})
            _=tailrefs
        _=refs
    report={'schema':'aion.ranked-correction-reduction-gate.v1',
            'status':'PASSED' if all(r['bitwise_equal'] for r in results) else 'FAILED',
            'results':results,'source_sha256':digest(source),'capture_metadata_sha256':digest(a.capture_stem.with_suffix('.json')),
            'sd_expert_reads':0,'threads':1,
            'claim_boundary':'Exact last-contribution integration audit on existing local cache. Reduced routes are diagnostic and are not quality-certified. No learned correction, elapsed-speed evidence or full-model promotion. Local L2 components checked read-only against source manifest; no cache admission or deletion.'}
    report['canonical_sha256']=canonical(report)
    with a.output.open('x') as handle:
        json.dump(report,handle,indent=2,sort_keys=True);handle.write('\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    main()
