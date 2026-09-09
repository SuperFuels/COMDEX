#!/usr/bin/env python3
"""Chain all 36 gpt-oss blocks and produce a first BOS-conditioned token."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from backend.modules.aion_inference.expert_frame_gguf_reader import ExpertFrameGGUFReader
from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index
from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore

WIDTH=2880; EXPERTS=128; BOS=199998

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(8*1024*1024): h.update(chunk)
    return h.hexdigest()

def compile_gate(source:Path,output:Path)->None:
    subprocess.run(['clang++','-std=c++17','-O3','-I/opt/homebrew/include',str(source),
                    '-L/opt/homebrew/lib','-lggml','-lggml-base','-ldl','-o',str(output)],check=True)

def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--threads',type=int,default=8);p.add_argument('--resident-replay',action='store_true');a=p.parse_args()
    if a.output.exists():raise SystemExit('refusing to overwrite evidence')
    manifest=json.loads(a.manifest.read_text()); sources=manifest['verified_sources']
    readers={}; tensor_index={}
    for source in sources:
        reader=ExpertFrameGGUFReader(a.manifest,source['name'],64*1024*1024);readers[source['name']]=reader
        idx=read_gguf_stream_index(reader,int(source['size']))
        for tensor in idx['tensors']: tensor_index[tensor['name']] = (source['name'],tensor)
    def read_tensor(name:str)->bytes:
        source,t=tensor_index[name];return readers[source].read_at(int(t['absolute_offset']),int(t['byte_length']))
    def write_tensor(name:str,path:Path)->dict:
        value=read_tensor(name);path.write_bytes(value);source,t=tensor_index[name]
        return {'source_shard':source,'ggml_type':int(t['ggml_type']),'dimensions':t['dimensions'],'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()}
    native=Path(__file__).parents[1]/'modules/aion_inference/native'
    with tempfile.TemporaryDirectory(prefix='aion-gptoss-first-token-') as temp:
        root=Path(temp); exe={}
        for key,file in [('embed','gptoss_embedding_cpu_gate.cpp'),('attention','gptoss_layer0_attention_cpu_gate.cpp'),('finish','gptoss_layer0_moe_finish_cpu_gate.cpp'),('output','gptoss_output_cpu_gate.cpp')]:
            exe[key]=root/key;compile_gate(native/file,exe[key])
        emb_name='token_embd.weight';source,t=tensor_index[emb_name]
        row_bytes=int(t['byte_length'])//int(t['dimensions'][1]); row_path=root/'embedding-row.bin'
        row=readers[source].read_at(int(t['absolute_offset'])+BOS*row_bytes,row_bytes);row_path.write_bytes(row)
        initial_hidden=root/'initial-hidden.bin'
        embed_run=json.loads(subprocess.check_output([str(exe['embed']),str(row_path),str(initial_hidden),str(a.threads)],text=True))
        output_weight=root/'vocabulary-output-weight.bin'; output_norm=root/'output-norm.bin'
        output_stage_started=time.perf_counter()
        # Stream the 615 MB vocabulary matrix so no equivalent Python allocation is created.
        source,ot=tensor_index['output.weight'];remaining=int(ot['byte_length']);offset=int(ot['absolute_offset'])
        with output_weight.open('wb') as f:
            while remaining:
                count=min(16*1024*1024,remaining);f.write(readers[source].read_at(offset,count));offset+=count;remaining-=count
        output_norm_evidence=write_tensor('output_norm.weight',output_norm)
        output_stage_seconds=time.perf_counter()-output_stage_started

        def layer_mapping(layer:int)->dict[str,str]:
            return {f'blk.{layer}.attn_norm.weight':'attn-norm-weight.bin',f'blk.{layer}.attn_q.weight':'q-weight.bin',f'blk.{layer}.attn_q.bias':'q-bias.bin',
                    f'blk.{layer}.attn_k.weight':'k-weight.bin',f'blk.{layer}.attn_k.bias':'k-bias.bin',f'blk.{layer}.attn_v.weight':'v-weight.bin',f'blk.{layer}.attn_v.bias':'v-bias.bin',
                    f'blk.{layer}.attn_sinks.weight':'attn-sinks-weight.bin',f'blk.{layer}.attn_output.weight':'output-weight.bin',f'blk.{layer}.attn_output.bias':'output-bias.bin',
                    f'blk.{layer}.post_attention_norm.weight':'post-attention-norm-weight.bin',f'blk.{layer}.ffn_gate_inp.weight':'router-weight.bin',f'blk.{layer}.ffn_gate_inp.bias':'router-bias.bin'}
        shared_stage_seconds=0.0
        if a.resident_replay:
            shared_stage_started=time.perf_counter()
            for layer in range(36):
                layer_root=root/f'shared-layer-{layer}';layer_root.mkdir()
                for name,file in layer_mapping(layer).items():(layer_root/file).write_bytes(read_tensor(name))
            shared_stage_seconds=time.perf_counter()-shared_stage_started
        persistent_store=GptOssExpertFrameStore(a.manifest,3*1024*1024*1024) if a.resident_replay else None

        def pass_once(label:str)->dict:
            store=persistent_store or GptOssExpertFrameStore(a.manifest,256*1024*1024);metrics_before=store.metrics();current=initial_hidden
            layers=[];started=time.perf_counter()
            for layer in range(36):
                mapping=layer_mapping(layer);layer_root=root/f'shared-layer-{layer}' if a.resident_replay else root
                shared_started=time.perf_counter()
                if not a.resident_replay:
                    for name,file in mapping.items(): (layer_root/file).write_bytes(read_tensor(name))
                shared_seconds=time.perf_counter()-shared_started
                prefix=root/f'{label}-layer-{layer}';attn=json.loads(subprocess.check_output([str(exe['attention']),str(layer_root),str(prefix),str(current),str(a.threads)],text=True))
                router_path=Path(str(prefix)+'-router-input.bin');ffn_path=Path(str(prefix)+'-ffn-input.bin')
                hidden=np.fromfile(router_path,dtype='<f4');w=np.fromfile(layer_root/'router-weight.bin',dtype='<f4').reshape(EXPERTS,WIDTH);b=np.fromfile(layer_root/'router-bias.bin',dtype='<f4')
                logits=w@hidden+b;route=np.argsort(logits,kind='stable')[-4:][::-1].astype(int).tolist();sel=logits[route].astype(np.float64);sel-=sel.max();gates=np.exp(sel);gates/=gates.sum()
                load_started=time.perf_counter();values=store.get_layer_route_parallel(layer,route,workers=4);load_seconds=time.perf_counter()-load_started
                for pos,value in enumerate(values):
                    for proj in ('gate','up','down'):
                        for kind in ('weight','bias'):(layer_root/f'{pos}-{proj}-{kind}.bin').write_bytes(value[proj][kind])
                next_hidden=root/f'{label}-layer-{layer}-output.bin';finish=json.loads(subprocess.check_output([str(exe['finish']),str(layer_root),','.join(map(str,route)),','.join(f'{x:.9g}' for x in gates),str(ffn_path),str(router_path),str(next_hidden),str(a.threads)],text=True))
                layers.append({'layer':layer,'route':route,'gates':gates.tolist(),'shared_load_seconds':shared_seconds,'expert_load_seconds':load_seconds,'attention':attn,'finish':finish,'output_sha256':sha(next_hidden)})
                if current != initial_hidden: current.unlink(missing_ok=True)
                Path(str(prefix)+'-ffn-input.bin').unlink(missing_ok=True);router_path.unlink(missing_ok=True);current=next_hidden
            logits_path=root/f'{label}-logits.bin';output=json.loads(subprocess.check_output([str(exe['output']),str(output_weight),str(output_norm),str(current),str(logits_path),str(a.threads)],text=True))
            metrics_after=store.metrics();delta={key:metrics_after[key]-metrics_before.get(key,0) for key in ('hits','faults','evictions','compressed_bytes_read','raw_bytes_materialized')}
            return {'label':label,'wall_seconds':time.perf_counter()-started,'layers':layers,'final_hidden_sha256':sha(current),'logits_sha256':sha(logits_path),'output':output,'store_metrics':metrics_after,'store_metric_delta':delta}
        run_a=pass_once('a');run_b=pass_once('b')
        routes_equal=[x['route'] for x in run_a['layers']]==[x['route'] for x in run_b['layers']]
        exact=(run_a['final_hidden_sha256']==run_b['final_hidden_sha256'] and run_a['logits_sha256']==run_b['logits_sha256'] and run_a['output']['argmax_token_id']==run_b['output']['argmax_token_id'])
        report={'schema':'aion.gptoss-first-token-gate.v1','status':'PASSED' if routes_equal and exact else 'FAILED','created_at':datetime.now(timezone.utc).isoformat(),
                'model':'GPT-OSS 120B Q4_K_M/MXFP4','input_token_id':BOS,'input_semantics':'GGUF-declared BOS token, one-token position-zero sequence','generated_token_id':run_a['output']['argmax_token_id'],
                'run_a':run_a,'run_b':run_b,'routes_repeatable':routes_equal,'final_hidden_and_logits_bitwise_repeatable':exact,
                'embedding_row_bytes':row_bytes,'embedding_row_sha256':hashlib.sha256(row).hexdigest(),'embedding_run':embed_run,
                'output_weight':{'bytes':output_weight.stat().st_size,'sha256':sha(output_weight),'one_time_stage_seconds':output_stage_seconds},'output_norm':output_norm_evidence,
                'reader_metrics':{name:r.metrics() for name,r in readers.items()},'resident_replay':a.resident_replay,'shared_one_time_stage_seconds':shared_stage_seconds,'declared_streaming_cache_bytes':(3*1024*1024*1024 if a.resident_replay else 256*1024*1024),'declared_largest_native_arena_bytes':768*1024*1024,
                'claim_boundary':'A BOS-conditioned position-zero sequence traversed embedding, all 36 attention/MoE blocks, final norm and vocabulary head to produce a finite repeatable argmax token. This is first-token execution evidence, not yet text-quality validation or steady-state generation speed.'}
        report['canonical_sha256']=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:report[k] for k in ('status','input_token_id','generated_token_id','routes_repeatable','final_hidden_and_logits_bitwise_repeatable','canonical_sha256')},sort_keys=True))
if __name__=='__main__':main()
