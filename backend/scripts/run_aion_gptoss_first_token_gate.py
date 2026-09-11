#!/usr/bin/env python3
"""Chain all 36 gpt-oss blocks and produce a first BOS-conditioned token."""
from __future__ import annotations
import argparse, ctypes, hashlib, json, subprocess, tempfile, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from backend.modules.aion_inference.expert_frame_gguf_reader import ExpertFrameGGUFReader
from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index
from backend.modules.aion_inference.gptoss_expert_frame_store import (
    ctypes_component_pointer_array,
    GptOssCompressedExpertFrameStore, GptOssExpertFrameStore,
    GptOssMappedPersistentL2ExpertFrameStore,
    GptOssPinnedVerifiedPersistentL2ExpertFrameStore,
    GptOssPersistentL2ExpertFrameStore,
    GptOssReusableArenaPersistentL2ExpertFrameStore,
    GptOssTieredExpertFrameStore,
)

WIDTH=2880; EXPERTS=128; BOS=199998

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(8*1024*1024): h.update(chunk)
    return h.hexdigest()

def compile_gate(source:Path,output:Path)->None:
    subprocess.run(['clang++','-std=c++17','-O3','-I/opt/homebrew/include',str(source),
                    '-L/opt/homebrew/lib','-lggml','-lggml-base','-ldl','-o',str(output)],check=True)

def overlap_enabled_for_pass(enabled:bool,pattern:str|None,index:int)->bool:
    return enabled and (pattern is None or pattern[index]=='1')

def should_overlap_layer(enabled:bool,missing_experts:int)->bool:
    # Splitting the fused four-expert calculation has a fixed cost.  The live
    # gate showed that cost is repaid only when at least two L2 reads can be
    # hidden behind already-available expert arithmetic.
    return enabled and missing_experts>=2

def parse_layer_spec(spec:str|None)->set[int]:
    if spec is None:
        return set(range(36))
    layers:set[int]=set()
    for item in spec.split(','):
        bounds=item.split('-',1)
        start=int(bounds[0]);end=int(bounds[-1])
        if start>end or start<0 or end>=36:
            raise ValueError('adaptive layer range must stay within 0..35')
        layers.update(range(start,end+1))
    if not layers:
        raise ValueError('adaptive layer selection must not be empty')
    return layers

def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--threads',type=int,default=8);p.add_argument('--resident-replay',action='store_true');p.add_argument('--compressed-cache',action='store_true');p.add_argument('--scan-resistant-cache',action='store_true');p.add_argument('--tiered-cache',action='store_true');p.add_argument('--persistent-l2-root',type=Path);p.add_argument('--persistent-l2-gib',type=float);p.add_argument('--l2-cartridge-plan',type=Path);p.add_argument('--l2-cartridge-family');p.add_argument('--l2-two-touch-admission',action='store_true');p.add_argument('--l2-admission-touches',type=int,default=2);p.add_argument('--route-arena-l1-hotset',action='store_true');p.add_argument('--overlap-l2-read-compute',action='store_true');p.add_argument('--overlap-pass-pattern');p.add_argument('--mapped-persistent-l2',action='store_true');p.add_argument('--pinned-verified-persistent-l2',action='store_true');p.add_argument('--reusable-arena-persistent-l2',action='store_true');p.add_argument('--mapped-l2-willneed',action='store_true');p.add_argument('--mapped-l2-parallel-prefault',action='store_true');p.add_argument('--inprocess-finish',action='store_true');p.add_argument('--parallel-moe',action='store_true');p.add_argument('--inprocess-attention',action='store_true');p.add_argument('--inprocess-output',action='store_true');p.add_argument('--inmemory-layer-flow',action='store_true');p.add_argument('--token-count',type=int,default=1);p.add_argument('--passes',type=int,default=2);p.add_argument('--input-token-id',type=int,default=BOS);p.add_argument('--input-token-ids');p.add_argument('--expert-pool',type=Path);p.add_argument('--constrain-after-prompt',action='store_true');p.add_argument('--exact-pool-escape-after-prompt',action='store_true');p.add_argument('--incremental-pool-admission',action='store_true');p.add_argument('--expert-cache-gib',type=float,default=3.0);p.add_argument('--preload-expert-pool',action='store_true');p.add_argument('--continuation-active-experts',type=int,default=4);p.add_argument('--continuation-gate-mass-threshold',type=float);p.add_argument('--continuation-adaptive-layers');p.add_argument('--preserve-dropped-gate-mass',action='store_true');p.add_argument('--activation-capture-dir',type=Path);p.add_argument('--capture-positions');p.add_argument('--capture-layers');a=p.parse_args()
    if a.parallel_moe and not a.inprocess_finish: raise SystemExit('--parallel-moe requires --inprocess-finish')
    if a.token_count < 1: raise SystemExit('token-count must be positive')
    if a.passes < 2: raise SystemExit('passes must be at least 2')
    forced_input_ids=([int(value) for value in a.input_token_ids.split(',') if value]
                      if a.input_token_ids else [a.input_token_id])
    if not forced_input_ids: raise SystemExit('input-token-ids must not be empty')
    if len(forced_input_ids)>a.token_count: raise SystemExit('token-count must cover all forced input tokens')
    if a.inprocess_attention and not a.resident_replay: raise SystemExit('in-process attention currently requires resident replay')
    if a.inmemory_layer_flow and not (a.inprocess_attention and a.inprocess_finish and a.inprocess_output): raise SystemExit('--inmemory-layer-flow requires all in-process stages')
    if a.expert_cache_gib <= 0: raise SystemExit('expert-cache-gib must be positive')
    if bool(a.persistent_l2_root) != bool(a.persistent_l2_gib): raise SystemExit('persistent L2 requires both root and capacity')
    if a.persistent_l2_gib is not None and a.persistent_l2_gib <= 0: raise SystemExit('persistent-l2-gib must be positive')
    if bool(a.l2_cartridge_plan) != bool(a.l2_cartridge_family): raise SystemExit('L2 cartridge requires both plan and family')
    if a.l2_cartridge_plan and not a.persistent_l2_root: raise SystemExit('L2 cartridge requires persistent L2')
    if a.l2_two_touch_admission and not (a.persistent_l2_root and a.l2_cartridge_plan): raise SystemExit('two-touch L2 admission requires a persistent family cartridge')
    if a.l2_admission_touches < 2: raise SystemExit('L2 admission touches must be at least two')
    if a.l2_admission_touches != 2 and not a.l2_two_touch_admission: raise SystemExit('custom L2 admission touches require two-touch admission mode')
    if a.route_arena_l1_hotset and not (a.reusable_arena_persistent_l2 and a.l2_cartridge_plan and a.preload_expert_pool): raise SystemExit('route-arena L1 hotset requires reusable arena, cartridge plan and preloaded pool')
    if a.overlap_l2_read_compute and not (a.reusable_arena_persistent_l2 and a.inprocess_finish): raise SystemExit('L2 read/compute overlap requires reusable arena and in-process finish')
    if a.overlap_l2_read_compute and (a.parallel_moe or a.mapped_l2_willneed or a.mapped_l2_parallel_prefault): raise SystemExit('L2 read/compute overlap is incompatible with other expert execution probes')
    if a.overlap_pass_pattern and (not a.overlap_l2_read_compute or len(a.overlap_pass_pattern)!=a.passes or set(a.overlap_pass_pattern)-set('01')): raise SystemExit('overlap pass pattern requires overlap mode and exactly one 0/1 character per pass')
    if a.persistent_l2_root and not a.resident_replay: raise SystemExit('persistent L2 requires resident replay')
    if a.persistent_l2_root and (a.compressed_cache or a.tiered_cache): raise SystemExit('persistent L2 cannot be combined with compressed or tiered cache modes')
    if a.mapped_persistent_l2 and not a.persistent_l2_root: raise SystemExit('mapped persistent L2 requires persistent L2')
    if a.pinned_verified_persistent_l2 and not a.persistent_l2_root: raise SystemExit('pinned verified persistent L2 requires persistent L2')
    if a.reusable_arena_persistent_l2 and not a.persistent_l2_root: raise SystemExit('reusable arena persistent L2 requires persistent L2')
    if sum((a.pinned_verified_persistent_l2,a.mapped_persistent_l2,a.reusable_arena_persistent_l2))>1: raise SystemExit('choose one persistent L2 access mode')
    if a.mapped_l2_willneed and not a.mapped_persistent_l2: raise SystemExit('mapped L2 willneed requires mapped persistent L2')
    if a.mapped_l2_parallel_prefault and not a.mapped_persistent_l2: raise SystemExit('parallel prefault requires mapped persistent L2')
    if a.mapped_l2_parallel_prefault and a.mapped_l2_willneed: raise SystemExit('choose one mapped L2 prefetch mode')
    if a.continuation_active_experts not in (1,2,3,4): raise SystemExit('continuation-active-experts must be 1..4')
    if a.continuation_active_experts != 4 and not (a.expert_pool and a.constrain_after_prompt): raise SystemExit('reduced continuation experts require a constrained post-prompt quality track')
    if a.continuation_gate_mass_threshold is not None and not (0.5<a.continuation_gate_mass_threshold<1.0): raise SystemExit('continuation-gate-mass-threshold must be between 0.5 and 1')
    if a.continuation_gate_mass_threshold is not None and not (a.expert_pool and (a.constrain_after_prompt or a.exact_pool_escape_after_prompt)): raise SystemExit('adaptive continuation experts require a preloaded pool plus constrained routing or exact unrestricted escape')
    if a.continuation_adaptive_layers and a.continuation_gate_mass_threshold is None: raise SystemExit('adaptive layer selection requires a gate-mass threshold')
    if a.preserve_dropped_gate_mass and not (a.continuation_active_experts != 4 or a.continuation_gate_mass_threshold is not None): raise SystemExit('preserving dropped mass requires a reduced-expert continuation')
    if a.preload_expert_pool and not (a.expert_pool and a.resident_replay): raise SystemExit('pool preload requires --expert-pool and --resident-replay')
    if a.constrain_after_prompt and not a.expert_pool: raise SystemExit('--constrain-after-prompt requires --expert-pool')
    if a.exact_pool_escape_after_prompt and not (a.expert_pool and a.preload_expert_pool and a.resident_replay): raise SystemExit('--exact-pool-escape-after-prompt requires a preloaded resident expert pool')
    if a.exact_pool_escape_after_prompt and a.constrain_after_prompt: raise SystemExit('exact pool escape and constrained routing are mutually exclusive')
    if a.incremental_pool_admission and not (a.constrain_after_prompt and a.resident_replay): raise SystemExit('--incremental-pool-admission requires a resident post-prompt pool')
    if a.incremental_pool_admission and a.preload_expert_pool: raise SystemExit('incremental admission and full preload are mutually exclusive')
    if a.output.exists():raise SystemExit('refusing to overwrite evidence')
    capture_positions=({int(value) for value in a.capture_positions.split(',') if value} if a.capture_positions else set())
    capture_layers=({int(value) for value in a.capture_layers.split(',') if value} if a.capture_layers else set())
    try: adaptive_layers=parse_layer_spec(a.continuation_adaptive_layers)
    except ValueError as error: raise SystemExit(str(error)) from error
    if bool(a.activation_capture_dir) != bool(capture_positions and capture_layers): raise SystemExit('activation capture requires a directory plus non-empty positions and layers')
    if a.activation_capture_dir and not a.inprocess_attention: raise SystemExit('activation capture requires in-process attention')
    if any(value<0 or value>=a.token_count for value in capture_positions): raise SystemExit('capture position is outside token-count')
    if any(value<0 or value>=36 for value in capture_layers): raise SystemExit('capture layer is outside 0..35')
    if a.activation_capture_dir: a.activation_capture_dir.mkdir(parents=True,exist_ok=False)
    manifest=json.loads(a.manifest.read_text()); sources=manifest['verified_sources']
    cartridge=None;cartridge_sha=None;cartridge_layers=None;cartridge_hotset_layers=None
    if a.l2_cartridge_plan:
        cartridge=json.loads(a.l2_cartridge_plan.read_text());cartridge_sha=cartridge.get('canonical_sha256');cartridge_body=dict(cartridge);cartridge_body.pop('canonical_sha256',None)
        calculated=hashlib.sha256(json.dumps(cartridge_body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        plan=cartridge.get('recommended_plan',{});families=plan.get('cartridges',{})
        if (cartridge.get('schema')!='aion.gptoss-120b-exact-family-cartridge-analysis.v1' or cartridge.get('status')!='OFFLINE_ANALYSIS_COMPLETE' or cartridge_sha!=calculated): raise SystemExit('L2 cartridge plan failed schema/hash verification')
        if cartridge.get('manifest_sha256')!=sha(a.manifest): raise SystemExit('L2 cartridge plan targets a different warehouse manifest')
        if a.l2_cartridge_family not in families: raise SystemExit('L2 cartridge family is absent from plan')
        if abs(float(plan.get('capacity_gib',-1))-float(a.persistent_l2_gib))>1e-9: raise SystemExit('L2 cartridge plan capacity differs from runtime capacity')
        selected=plan.get('core',[])+families[a.l2_cartridge_family]
        if any(set(item)!={'compressed_bytes','expert','layer','raw_bytes'} or not 0<=int(item['layer'])<36 or not 0<=int(item['expert'])<128 for item in selected): raise SystemExit('L2 cartridge contains an invalid expert entry')
        cartridge_layers={str(layer):sorted({int(item['expert']) for item in selected if int(item['layer'])==layer}) for layer in range(36)}
        if a.route_arena_l1_hotset:
            hotsets=plan.get('ram_hotsets',{});hot=hotsets.get(a.l2_cartridge_family,{}).get('entries',[])
            if not hot or any(not 0<=int(item.get('layer',-1))<36 or not 0<=int(item.get('expert',-1))<128 for item in hot): raise SystemExit('L2 cartridge has no valid RAM hotset for selected family')
            cartridge_hotset_layers={str(layer):sorted({int(item['expert']) for item in hot if int(item['layer'])==layer}) for layer in range(36)}
    expert_pool=None;expert_pool_sha=None
    if a.expert_pool:
        expert_pool=json.loads(a.expert_pool.read_text());claimed=expert_pool.get('canonical_sha256');body=dict(expert_pool);body.pop('canonical_sha256',None)
        if (expert_pool.get('schema')!='aion.gptoss-120b-constrained-expert-pool.v1' or not expert_pool.get('quality_track') or claimed!=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()): raise SystemExit('expert pool failed schema/hash verification')
        if set(expert_pool.get('layers',{}))!={str(layer) for layer in range(36)}: raise SystemExit('expert pool layer coverage is incomplete')
        if any(len(values)<4 or len(values)!=len(set(values)) or any(not 0<=value<128 for value in values) for values in expert_pool['layers'].values()): raise SystemExit('expert pool contains invalid layer experts')
        expert_pool_sha=claimed
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
        moe_function=None;prefault_function=None;contribution_function=None;combine_function=None
        if a.inprocess_finish:
            library=root/'libaion-gptoss-moe.dylib'
            subprocess.run(['clang++','-std=c++17','-O3','-dynamiclib','-I/opt/homebrew/include',str(native/'gptoss_persistent_moe_library.cpp'),'-L/opt/homebrew/lib','-lggml','-lggml-base','-ldl','-o',str(library)],check=True)
            loaded=ctypes.CDLL(str(library));moe_function=loaded.aion_gptoss_moe_finish
            if a.parallel_moe: moe_function=loaded.aion_gptoss_moe_finish_parallel
            reduced_moe_function=loaded.aion_gptoss_moe_finish_active
            prefault_function=loaded.aion_gptoss_prefault_components
            contribution_function=loaded.aion_gptoss_one_expert_contribution_batch
            combine_function=loaded.aion_gptoss_combine_four_contributions
            moe_function.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float),ctypes.c_int,ctypes.POINTER(ctypes.c_double)];moe_function.restype=ctypes.c_int
            reduced_moe_function.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_float),ctypes.c_int,ctypes.POINTER(ctypes.c_float),ctypes.c_int,ctypes.POINTER(ctypes.c_double)];reduced_moe_function.restype=ctypes.c_int
            prefault_function.argtypes=[ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_size_t),ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_uint64),ctypes.POINTER(ctypes.c_double)];prefault_function.restype=ctypes.c_int
            contribution_function.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_float),ctypes.c_int,ctypes.POINTER(ctypes.c_float),ctypes.c_int,ctypes.POINTER(ctypes.c_double)];contribution_function.restype=ctypes.c_int
            combine_function.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float),ctypes.c_int,ctypes.POINTER(ctypes.c_float)];combine_function.restype=ctypes.c_int
        attention_function=None;attention_reset=None
        if a.inprocess_attention:
            library=root/'libaion-gptoss-attention.dylib'
            subprocess.run(['clang++','-std=c++17','-O3','-dynamiclib','-I/opt/homebrew/include',str(native/'gptoss_persistent_attention_library.cpp'),'-L/opt/homebrew/lib','-lggml','-lggml-base','-ldl','-o',str(library)],check=True)
            attention_loaded=ctypes.CDLL(str(library));attention_function=attention_loaded.aion_gptoss_attention;attention_reset=attention_loaded.aion_gptoss_attention_reset_kv
            attention_function.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_void_p),ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float),ctypes.c_int,ctypes.POINTER(ctypes.c_double)];attention_function.restype=ctypes.c_int
            attention_reset.argtypes=[];attention_reset.restype=None
        output_function=None
        if a.inprocess_output:
            library=root/'libaion-gptoss-output.dylib'
            subprocess.run(['clang++','-std=c++17','-O3','-dynamiclib','-I/opt/homebrew/include',str(native/'gptoss_persistent_output_library.cpp'),'-L/opt/homebrew/lib','-lggml','-lggml-base','-ldl','-o',str(library)],check=True)
            output_loaded=ctypes.CDLL(str(library));output_function=output_loaded.aion_gptoss_output
            output_function.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float),ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_double)];output_function.restype=ctypes.c_int
        emb_name='token_embd.weight';source,t=tensor_index[emb_name]
        row_bytes=int(t['byte_length'])//int(t['dimensions'][1])
        def embed(token_id:int,label:str)->tuple[Path,dict,str]:
            row=readers[source].read_at(int(t['absolute_offset'])+token_id*row_bytes,row_bytes);row_path=root/f'{label}-embedding-row.bin';row_path.write_bytes(row);hidden=root/f'{label}-initial-hidden.bin'
            run=json.loads(subprocess.check_output([str(exe['embed']),str(row_path),str(hidden),str(a.threads)],text=True));return hidden,run,hashlib.sha256(row).hexdigest()
        if any(not 0 <= token < int(t['dimensions'][1]) for token in forced_input_ids):
            raise SystemExit('an input token ID is outside the model vocabulary')
        initial_hidden,embed_run,initial_row_sha=embed(forced_input_ids[0],'initial')
        output_weight=root/'vocabulary-output-weight.bin'; output_norm=root/'output-norm.bin'
        output_stage_started=time.perf_counter()
        # Stream the 615 MB vocabulary matrix so no equivalent Python allocation is created.
        source,ot=tensor_index['output.weight'];remaining=int(ot['byte_length']);offset=int(ot['absolute_offset'])
        with output_weight.open('wb') as f:
            while remaining:
                count=min(16*1024*1024,remaining);f.write(readers[source].read_at(offset,count));offset+=count;remaining-=count
        output_norm_value=read_tensor('output_norm.weight');output_norm.write_bytes(output_norm_value);source,nt=tensor_index['output_norm.weight'];output_norm_evidence={'source_shard':source,'ggml_type':int(nt['ggml_type']),'dimensions':nt['dimensions'],'bytes':len(output_norm_value),'sha256':hashlib.sha256(output_norm_value).hexdigest()}
        output_stage_seconds=time.perf_counter()-output_stage_started
        output_weight_view=np.memmap(output_weight,dtype=np.uint8,mode='r') if a.inprocess_output else None
        output_norm_view=np.frombuffer(output_norm_value,dtype='<f4') if a.inprocess_output else None

        def layer_mapping(layer:int)->dict[str,str]:
            return {f'blk.{layer}.attn_norm.weight':'attn-norm-weight.bin',f'blk.{layer}.attn_q.weight':'q-weight.bin',f'blk.{layer}.attn_q.bias':'q-bias.bin',
                    f'blk.{layer}.attn_k.weight':'k-weight.bin',f'blk.{layer}.attn_k.bias':'k-bias.bin',f'blk.{layer}.attn_v.weight':'v-weight.bin',f'blk.{layer}.attn_v.bias':'v-bias.bin',
                    f'blk.{layer}.attn_sinks.weight':'attn-sinks-weight.bin',f'blk.{layer}.attn_output.weight':'output-weight.bin',f'blk.{layer}.attn_output.bias':'output-bias.bin',
                    f'blk.{layer}.post_attention_norm.weight':'post-attention-norm-weight.bin',f'blk.{layer}.ffn_gate_inp.weight':'router-weight.bin',f'blk.{layer}.ffn_gate_inp.bias':'router-bias.bin'}
        shared_stage_seconds=0.0;attention_resident=[];router_resident=[]
        if a.resident_replay:
            shared_stage_started=time.perf_counter()
            for layer in range(36):
                layer_root=root/f'shared-layer-{layer}';layer_root.mkdir()
                resident={}
                for name,file in layer_mapping(layer).items():
                    value=read_tensor(name);resident[file]=value
                    if not a.inprocess_attention: (layer_root/file).write_bytes(value)
                if a.inprocess_attention:
                    attention_resident.append([resident[name] for name in ('attn-norm-weight.bin','q-weight.bin','q-bias.bin','k-weight.bin','k-bias.bin','v-weight.bin','v-bias.bin','attn-sinks-weight.bin','output-weight.bin','output-bias.bin','post-attention-norm-weight.bin')])
                    router_resident.append((resident['router-weight.bin'],resident['router-bias.bin']))
            shared_stage_seconds=time.perf_counter()-shared_stage_started
        expert_cache_bytes=int(a.expert_cache_gib*1024*1024*1024)
        if a.resident_replay and a.persistent_l2_root:
            persistent_l2_type=(GptOssMappedPersistentL2ExpertFrameStore
                                if a.mapped_persistent_l2 else
                                GptOssReusableArenaPersistentL2ExpertFrameStore
                                if a.reusable_arena_persistent_l2 else
                                GptOssPinnedVerifiedPersistentL2ExpertFrameStore
                                if a.pinned_verified_persistent_l2 else
                                GptOssPersistentL2ExpertFrameStore)
            persistent_store=persistent_l2_type(
                a.manifest,expert_cache_bytes,a.persistent_l2_root,
                int(a.persistent_l2_gib*1024*1024*1024))
        else:
            store_type=GptOssTieredExpertFrameStore if a.tiered_cache else GptOssCompressedExpertFrameStore if a.compressed_cache else GptOssExpertFrameStore
            persistent_store=(store_type(a.manifest,expert_cache_bytes,
                              freeze_when_full=a.scan_resistant_cache)
                              if a.resident_replay and a.compressed_cache and not a.tiered_cache else
                              store_type(a.manifest,expert_cache_bytes) if a.resident_replay else None)
        if a.incremental_pool_admission:
            persistent_store.set_admission_allowlist(expert_pool['layers'])
        if a.preload_expert_pool and a.persistent_l2_root:
            persistent_store.set_l2_bypass(expert_pool['layers'])
        if cartridge_layers is not None:
            bypass={(int(layer),expert) for layer,experts in (expert_pool['layers'].items() if a.preload_expert_pool else []) for expert in experts}
            protected={layer:[expert for expert in experts if (int(layer),expert) not in bypass] for layer,experts in cartridge_layers.items()}
            persistent_store.set_l2_protected(protected)
        if a.l2_two_touch_admission:
            persistent_store.set_l2_two_touch_admission(required_touches=a.l2_admission_touches)
        if cartridge_hotset_layers is not None:
            persistent_store.set_route_arena_l1_allowlist(cartridge_hotset_layers)
        pool_preload_seconds=0.0;pool_preload_metrics=None
        if a.preload_expert_pool:
            preload_started=time.perf_counter()
            for layer in range(36):
                persistent_store.get_layer_route_parallel(layer,expert_pool['layers'][str(layer)],workers=4)
            pool_preload_seconds=time.perf_counter()-preload_started
            pool_preload_metrics=persistent_store.metrics()
            if pool_preload_metrics['resident_bytes']>expert_cache_bytes: raise RuntimeError('expert pool exceeded declared cache')
            if a.constrain_after_prompt or a.exact_pool_escape_after_prompt:
                persistent_store.protect(expert_pool['layers'])

        def pass_once(label:str)->dict:
            pass_index=ord(label)-ord('a')
            overlap_enabled=overlap_enabled_for_pass(
                a.overlap_l2_read_compute,a.overlap_pass_pattern,pass_index)
            store=persistent_store or GptOssExpertFrameStore(a.manifest,256*1024*1024);metrics_before=store.metrics();token_id=forced_input_ids[0]
            if a.inprocess_attention: attention_reset()
            token_results=[];started=time.perf_counter();transition_rehydrate_seconds=0.0;transition_rehydrate_delta=None
            for position in range(a.token_count):
              if (position==len(forced_input_ids) and a.constrain_after_prompt
                      and (a.preload_expert_pool or a.incremental_pool_admission)):
                rehydrate_before=store.metrics();rehydrate_started=time.perf_counter()
                for layer in range(36):
                    store.get_layer_route_parallel(layer,expert_pool['layers'][str(layer)],workers=4)
                transition_rehydrate_seconds=time.perf_counter()-rehydrate_started
                rehydrate_after=store.metrics();transition_rehydrate_delta={
                    key:rehydrate_after[key]-rehydrate_before.get(key,0)
                    for key in ('hits','faults','evictions','compressed_bytes_read','raw_bytes_materialized')}
                if a.incremental_pool_admission:
                    store.protect(expert_pool['layers'])
              input_token_id=(forced_input_ids[position] if position<len(forced_input_ids) else token_id)
              current,embedding,embedding_sha=(initial_hidden,embed_run,initial_row_sha) if position==0 else embed(input_token_id,f'{label}-token-{position}')
              current_values=np.fromfile(current,dtype='<f4') if a.inmemory_layer_flow else None
              layers=[];token_started=time.perf_counter()
              for layer in range(36):
                mapping=layer_mapping(layer);layer_root=root/f'shared-layer-{layer}' if a.resident_replay else root
                shared_started=time.perf_counter()
                if not a.resident_replay:
                    for name,file in mapping.items(): (layer_root/file).write_bytes(read_tensor(name))
                shared_seconds=time.perf_counter()-shared_started
                prefix=root/f'{label}-token-{position}-layer-{layer}'
                router_path=Path(str(prefix)+'-router-input.bin');ffn_path=Path(str(prefix)+'-ffn-input.bin')
                attention_started=time.perf_counter()
                if a.inprocess_attention:
                    attention_input=current_values if a.inmemory_layer_flow else np.fromfile(current,dtype='<f4');ffn_result=np.empty(WIDTH,dtype=np.float32);router_result=np.empty(WIDTH,dtype=np.float32);attention_elapsed=ctypes.c_double()
                    references=[ctypes.c_char_p(blob) for blob in attention_resident[layer]];pointers=(ctypes.c_void_p*len(references))(*[ctypes.cast(ref,ctypes.c_void_p).value for ref in references])
                    value_is_q5=int(len(attention_resident[layer][5])==1013760)
                    status=attention_function(attention_input.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),pointers,value_is_q5,layer,position,ffn_result.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),router_result.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),a.threads,ctypes.byref(attention_elapsed))
                    if status: raise RuntimeError(f'in-process attention failed: {status}')
                    if not a.inmemory_layer_flow:
                        ffn_path.write_bytes(ffn_result.tobytes());router_path.write_bytes(router_result.tobytes())
                    attn={'schema':'aion.gptoss.persistent-attention-position-zero.v1','compute_ms':attention_elapsed.value,'finite':True}
                else:
                    attention_command=[str(exe['attention']),str(layer_root),str(prefix),str(current)]
                    if a.token_count > 1: attention_command += [str(position),str(root/f'{label}-kv-layer-{layer}')]
                    attention_command += [str(a.threads)]
                    attn=json.loads(subprocess.check_output(attention_command,text=True))
                attention_seconds=time.perf_counter()-attention_started
                hidden=router_result if a.inmemory_layer_flow else np.fromfile(router_path,dtype='<f4')
                if a.inprocess_attention:
                    w=np.frombuffer(router_resident[layer][0],dtype='<f4').reshape(EXPERTS,WIDTH);b=np.frombuffer(router_resident[layer][1],dtype='<f4')
                else:
                    w=np.fromfile(layer_root/'router-weight.bin',dtype='<f4').reshape(EXPERTS,WIDTH);b=np.fromfile(layer_root/'router-bias.bin',dtype='<f4')
                logits=w@hidden+b
                constrain_route=(expert_pool is not None and not a.exact_pool_escape_after_prompt
                                 and (not a.constrain_after_prompt or position>=len(forced_input_ids)))
                adaptive_here=(a.continuation_gate_mass_threshold is not None and
                               position>=len(forced_input_ids) and layer in adaptive_layers)
                active_experts=(a.continuation_active_experts if position>=len(forced_input_ids) else 4)
                if a.continuation_gate_mass_threshold is not None and not adaptive_here:
                    active_experts=4
                candidate_count=(4 if (adaptive_here or a.preserve_dropped_gate_mass) and position>=len(forced_input_ids) else active_experts)
                if constrain_route:
                    eligible=np.asarray(expert_pool['layers'][str(layer)],dtype=np.int64);local=np.argsort(logits[eligible],kind='stable')[-candidate_count:][::-1];route=eligible[local].astype(int).tolist()
                else: route=np.argsort(logits,kind='stable')[-candidate_count:][::-1].astype(int).tolist()
                route_pool_complete=(expert_pool is not None and
                                     all(expert in expert_pool['layers'][str(layer)] for expert in route))
                sel=logits[route].astype(np.float64);sel-=sel.max();gates=np.exp(sel);gates/=gates.sum()
                if adaptive_here:
                    threshold=a.continuation_gate_mass_threshold
                    active_experts=(2 if gates[:2].sum()>=threshold else 3 if gates[:3].sum()>=threshold else 4)
                    route=route[:active_experts];gates=gates[:active_experts]
                    if not a.preserve_dropped_gate_mass:gates/=gates.sum()
                elif active_experts < candidate_count:
                    route=route[:active_experts];gates=gates[:active_experts]
                    if not a.preserve_dropped_gate_mass:gates/=gates.sum()
                capture_stem=None
                if (a.activation_capture_dir and label=='a'
                        and position in capture_positions and layer in capture_layers):
                    capture_stem=a.activation_capture_dir/f'position-{position}-layer-{layer}'
                prepared_components=None;prefault_ms=0.0;prefault_checksum=None;overlap_seconds=0.0
                next_hidden=root/f'{label}-token-{position}-layer-{layer}-output.bin'
                overlap_missing_experts=(sum((layer,expert) not in store._cache for expert in route)
                                         if overlap_enabled else 0)
                # The exact overlap primitive currently evaluates four expert
                # contributions.  Adaptive continuation may deliberately keep
                # only two or three.  Those layers must use the reduced native
                # kernel, while unchanged four-expert layers can still hide L2
                # delivery behind useful calculation.
                overlap_applied=(active_experts == 4 and
                                 should_overlap_layer(overlap_enabled,overlap_missing_experts))
                if overlap_applied:
                    ffn=ffn_result if a.inmemory_layer_flow else np.fromfile(ffn_path,dtype='<f4');router_values=router_result if a.inmemory_layer_flow else np.fromfile(router_path,dtype='<f4');gate_values=np.asarray([float(f'{x:.9g}') for x in gates],dtype=np.float32)
                    contributions=np.empty((4,WIDTH),dtype=np.float32);native_ms=0.0;overlap_started=time.perf_counter();cached=[];missing=[]
                    for slot,expert in enumerate(route):
                        key=(layer,expert);value=store._cache.pop(key,None)
                        if value is None: store.faults+=1;missing.append((slot,expert))
                        else: store.hits+=1;store._cache[key]=value;cached.append((slot,value))
                    def calculate_contribution(slot,value):
                        blobs=[value[proj][kind] for proj in ('gate','up','down') for kind in ('weight','bias')]
                        references,pointers=ctypes_component_pointer_array(blobs);one_gate=np.asarray([gate_values[slot]],dtype=np.float32);elapsed=ctypes.c_double()
                        status=contribution_function(router_values.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),pointers,one_gate.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),1,contributions[slot].ctypes.data_as(ctypes.POINTER(ctypes.c_float)),a.threads,ctypes.byref(elapsed))
                        if status: raise RuntimeError(f'overlapped expert contribution failed: {status}')
                        _=references
                        return elapsed.value
                    with ThreadPoolExecutor(max_workers=max(1,len(missing)),thread_name_prefix='aion-overlap-read') as pool:
                        futures={pool.submit(store._read_l2_into_slot,layer,expert,slot):(slot,expert) for slot,expert in missing}
                        for slot,value in cached: native_ms+=calculate_contribution(slot,value)
                        for future in as_completed(futures):
                            slot,expert=futures[future];value=future.result()
                            if value is None:
                                store.sd_fallbacks+=1;value=GptOssExpertFrameStore._load_value(store,layer,expert);store._write_l2(layer,expert,value)
                            if a.route_arena_l1_hotset:
                                value=store.maybe_admit_route_arena_l1(layer,expert,value)
                            native_ms+=calculate_contribution(slot,value)
                    out=np.empty(WIDTH,dtype=np.float32)
                    status=combine_function(ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),contributions.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),1,out.ctypes.data_as(ctypes.POINTER(ctypes.c_float)))
                    if status: raise RuntimeError(f'overlapped expert combine failed: {status}')
                    overlap_seconds=time.perf_counter()-overlap_started;load_seconds=0.0;expert_stage_seconds=0.0;finish_seconds=overlap_seconds
                    if a.inmemory_layer_flow: current_values=out
                    else: next_hidden.write_bytes(out.tobytes())
                    finish={'schema':'aion.gptoss.overlapped-persistent-moe.v1','compute_ms':native_ms,'output_checksum':float(out.astype(np.float64).sum()),'finite':bool(np.isfinite(out).all())}
                else:
                    load_started=time.perf_counter();values=store.get_layer_route_parallel(layer,route,workers=4)
                    if a.mapped_l2_willneed: store.advise_route_willneed(values)
                    if a.mapped_l2_parallel_prefault:
                        blobs=[value[proj][kind] for value in values for proj in ('gate','up','down') for kind in ('weight','bias')]
                        references,pointers=ctypes_component_pointer_array(blobs);sizes=(ctypes.c_size_t*len(blobs))(*map(len,blobs));native_prefault_ms=ctypes.c_double();checksum=ctypes.c_uint64()
                        status=prefault_function(pointers,sizes,len(blobs),4,ctypes.byref(checksum),ctypes.byref(native_prefault_ms))
                        if status: raise RuntimeError(f'mapped L2 prefault failed: {status}')
                        prepared_components=(blobs,references,pointers);prefault_ms=native_prefault_ms.value;prefault_checksum=checksum.value
                    load_seconds=time.perf_counter()-load_started
                    expert_stage_started=time.perf_counter()
                    if not a.inprocess_finish:
                        for pos,value in enumerate(values):
                            for proj in ('gate','up','down'):
                                for kind in ('weight','bias'):(layer_root/f'{pos}-{proj}-{kind}.bin').write_bytes(value[proj][kind])
                    expert_stage_seconds=time.perf_counter()-expert_stage_started
                    finish_started=time.perf_counter()
                    if a.inprocess_finish:
                        ffn=ffn_result if a.inmemory_layer_flow else np.fromfile(ffn_path,dtype='<f4');router_values=router_result if a.inmemory_layer_flow else np.fromfile(router_path,dtype='<f4');gate_values=np.asarray([float(f'{x:.9g}') for x in gates],dtype=np.float32);out=np.empty(WIDTH,dtype=np.float32);elapsed=ctypes.c_double()
                        if prepared_components is None:
                            blobs=[value[proj][kind] for value in values for proj in ('gate','up','down') for kind in ('weight','bias')]
                            references,pointers=ctypes_component_pointer_array(blobs)
                        else: blobs,references,pointers=prepared_components
                        if active_experts == 4:
                            status=moe_function(ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),router_values.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),pointers,gate_values.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),out.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),a.threads,ctypes.byref(elapsed))
                        else:
                            status=reduced_moe_function(ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),router_values.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),pointers,gate_values.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),active_experts,out.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),a.threads,ctypes.byref(elapsed))
                        if status: raise RuntimeError(f'in-process MoE failed: {status}')
                        if a.inmemory_layer_flow: current_values=out
                        else: next_hidden.write_bytes(out.tobytes())
                        finish={'schema':'aion.gptoss.persistent-moe.v1','compute_ms':elapsed.value,'output_checksum':float(out.astype(np.float64).sum()),'finite':bool(np.isfinite(out).all())}
                    else:
                        finish=json.loads(subprocess.check_output([str(exe['finish']),str(layer_root),','.join(map(str,route)),','.join(f'{x:.9g}' for x in gates),str(ffn_path),str(router_path),str(next_hidden),str(a.threads)],text=True))
                    finish_seconds=time.perf_counter()-finish_started
                if capture_stem is not None:
                    output_values=(out if a.inprocess_finish else
                                   np.fromfile(next_hidden,dtype='<f4'))
                    ffn_capture=np.asarray(ffn_result,dtype='<f4')
                    router_capture=np.asarray(router_result,dtype='<f4')
                    output_capture=np.asarray(output_values,dtype='<f4')
                    # Store the observable four-expert contribution in F32.  The
                    # original output is retained too, allowing independent
                    # verification that target + residual input reconstructs it
                    # within the declared F32 subtraction/addition boundary.
                    residual_capture=np.asarray(output_capture-ffn_capture,dtype='<f4')
                    blobs={'ffn':ffn_capture.tobytes(),'router':router_capture.tobytes(),
                           'output':output_capture.tobytes(),'residual':residual_capture.tobytes()}
                    for name,value in blobs.items():
                        Path(str(capture_stem)+f'-{name}.bin').write_bytes(value)
                    metadata={
                        'schema':'aion.gptoss-120b-shadow-target-capture.v2',
                        'position':position,'layer':layer,'route':route,'gates':gates.tolist(),
                        **{f'{name}_sha256':hashlib.sha256(value).hexdigest()
                           for name,value in blobs.items()},
                        'target_definition':'F32 layer output minus F32 post-attention residual input',
                        'warehouse_manifest_canonical_sha256':manifest.get('canonical_sha256'),
                        'source_model_shards':[
                            {'name':source['name'],'sha256':source['verified_sha256']}
                            for source in sources],
                        'collection_implementation':'run_aion_gptoss_first_token_gate.py',
                        'collection_precision':'GGML MXFP4 expert arithmetic with F32 accumulation/output',
                        'contains_prompt_text':False,
                        'contains_personal_or_customer_data':False,
                    }
                    Path(str(capture_stem)+'.json').write_text(
                        json.dumps(metadata,indent=2,sort_keys=True)+'\n')
                layer_output_sha=(hashlib.sha256(current_values.tobytes()).hexdigest()
                                  if a.inmemory_layer_flow else sha(next_hidden))
                layers.append({'layer':layer,'route':route,'gates':gates.tolist(),'route_pool_complete':route_pool_complete,'shared_load_seconds':shared_seconds,'expert_load_seconds':load_seconds,'overlap_applied':overlap_applied,'overlap_missing_experts':overlap_missing_experts,'overlapped_expert_read_compute_seconds':overlap_seconds,'mapped_prefault_ms':prefault_ms,'mapped_prefault_checksum':prefault_checksum,'expert_file_stage_seconds':expert_stage_seconds,'attention_process_seconds':attention_seconds,'finish_process_seconds':finish_seconds,'attention':attn,'finish':finish,'output_sha256':layer_output_sha})
                if not a.inmemory_layer_flow:
                    if current != initial_hidden: current.unlink(missing_ok=True)
                    Path(str(prefix)+'-ffn-input.bin').unlink(missing_ok=True);router_path.unlink(missing_ok=True);current=next_hidden
              logits_path=root/f'{label}-token-{position}-logits.bin';output_started=time.perf_counter()
              if a.inprocess_output:
                  hidden_values=current_values if a.inmemory_layer_flow else np.fromfile(current,dtype='<f4');logit_values=np.empty(201088,dtype=np.float32);native_token=ctypes.c_int();checksum=ctypes.c_double();elapsed=ctypes.c_double()
                  status=output_function(ctypes.c_void_p(output_weight_view.ctypes.data),output_norm_view.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),hidden_values.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),logit_values.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),a.threads,ctypes.byref(native_token),ctypes.byref(checksum),ctypes.byref(elapsed))
                  if status: raise RuntimeError(f'in-process output failed: {status}')
                  if not a.inmemory_layer_flow: logits_path.write_bytes(logit_values.tobytes())
                  token_id=native_token.value;output={'schema':'aion.gptoss.persistent-output.v1','argmax_token_id':token_id,'max_logit':float(logit_values[token_id]),'logit_checksum':checksum.value,'finite':True,'compute_ms':elapsed.value}
              else:
                  output=json.loads(subprocess.check_output([str(exe['output']),str(output_weight),str(output_norm),str(current),str(logits_path),str(a.threads)],text=True));token_id=output['argmax_token_id']
              output_seconds=time.perf_counter()-output_started
              final_hidden_sha=(hashlib.sha256(current_values.tobytes()).hexdigest()
                                if a.inmemory_layer_flow else sha(current))
              logits_sha=(hashlib.sha256(logit_values.tobytes()).hexdigest()
                           if a.inmemory_layer_flow else sha(logits_path))
              token_results.append({'position':position,'input_token_id':input_token_id,'input_was_forced_prompt':position<len(forced_input_ids),'generated_token_id':token_id,'wall_seconds':time.perf_counter()-token_started,'output_process_seconds':output_seconds,'layers':layers,'final_hidden_sha256':final_hidden_sha,'logits_sha256':logits_sha,'output':output,'embedding':embedding,'embedding_row_sha256':embedding_sha})
            metrics_after=store.metrics()
            metric_keys=(
                'hits','faults','evictions','compressed_bytes_read','raw_bytes_materialized',
                'l2_hits','l2_misses','l2_bytes_read','l2_bytes_written','l2_evictions',
                'l2_integrity_failures','sd_fallbacks',
                'mapped_l2_hits','mapped_l2_view_reuses','mapped_l2_logical_bytes',
                'l2_verification_passes','l2_verification_reuses',
                'l2_verification_bytes','mapped_l2_willneed_calls',
                'route_arena_l1_admissions','route_arena_l1_admission_bytes',
            )
            delta={key:metrics_after[key]-metrics_before.get(key,0)
                   for key in metric_keys if key in metrics_after}
            return {'label':label,'overlap_enabled':overlap_enabled,'wall_seconds':time.perf_counter()-started,'tokens':token_results,'layers':token_results[-1]['layers'],'final_hidden_sha256':token_results[-1]['final_hidden_sha256'],'logits_sha256':token_results[-1]['logits_sha256'],'output':token_results[-1]['output'],'store_metrics':metrics_after,'store_metric_delta':delta,'prompt_to_continuation_rehydrate_seconds':transition_rehydrate_seconds,'prompt_to_continuation_rehydrate_metric_delta':transition_rehydrate_delta}
        runs=[pass_once(chr(ord('a')+index)) for index in range(a.passes)]
        run_a,run_b=runs[:2]
        route_sequences=[[[x['route'] for x in token['layers']] for token in run['tokens']] for run in runs]
        routes_equal=all(sequence==route_sequences[0] for sequence in route_sequences[1:])
        exact=(routes_equal and all(
            all(x['final_hidden_sha256']==y['final_hidden_sha256'] and x['logits_sha256']==y['logits_sha256'] and x['generated_token_id']==y['generated_token_id'] for x,y in zip(run_a['tokens'],run['tokens']))
            for run in runs[1:]))
        report={'schema':('aion.gptoss-multitoken-kv-gate.v1' if a.token_count>1 else 'aion.gptoss-first-token-gate.v1'),'status':'PASSED' if routes_equal and exact else 'FAILED','created_at':datetime.now(timezone.utc).isoformat(),
                'model':'GPT-OSS 120B Q4_K_M/MXFP4','input_token_id':forced_input_ids[0],'input_token_ids':forced_input_ids,'token_count':a.token_count,'input_semantics':('GGUF-declared BOS token followed by greedy argmax tokens with per-layer KV history' if forced_input_ids==[BOS] else 'Externally tokenized prompt tokens are teacher-forced in order, followed by greedy argmax tokens with per-layer KV history'),'generated_token_id':run_a['output']['argmax_token_id'],
                'run_a':run_a,'run_b':run_b,'additional_runs':runs[2:],'passes':a.passes,'routes_repeatable':routes_equal,'final_hidden_and_logits_bitwise_repeatable':exact,
                'embedding_row_bytes':row_bytes,'embedding_row_sha256':initial_row_sha,'embedding_run':embed_run,
                'output_weight':{'bytes':output_weight.stat().st_size,'sha256':sha(output_weight),'one_time_stage_seconds':output_stage_seconds},'output_norm':output_norm_evidence,'continuation_active_experts':a.continuation_active_experts,'continuation_gate_mass_threshold':a.continuation_gate_mass_threshold,'continuation_adaptive_layers':sorted(adaptive_layers) if a.continuation_gate_mass_threshold is not None else None,'preserve_dropped_gate_mass':a.preserve_dropped_gate_mass,
                'reader_metrics':{name:r.metrics() for name,r in readers.items()},'resident_replay':a.resident_replay,'compressed_expert_cache':a.compressed_cache,'scan_resistant_cache':a.scan_resistant_cache,'tiered_expert_cache':a.tiered_cache,'persistent_l2_root':str(a.persistent_l2_root.resolve()) if a.persistent_l2_root else None,'declared_persistent_l2_bytes':int(a.persistent_l2_gib*1024*1024*1024) if a.persistent_l2_gib else 0,'l2_cartridge_plan_path':str(a.l2_cartridge_plan.resolve()) if a.l2_cartridge_plan else None,'l2_cartridge_plan_canonical_sha256':cartridge_sha,'l2_cartridge_family':a.l2_cartridge_family,'l2_cartridge_protected_entries':sum(map(len,cartridge_layers.values())) if cartridge_layers else 0,'l2_cartridge_eager_prefetch':False,'l2_two_touch_admission':a.l2_two_touch_admission,'l2_admission_touches':a.l2_admission_touches,'route_arena_l1_hotset':a.route_arena_l1_hotset,'route_arena_l1_hotset_entries':sum(map(len,cartridge_hotset_layers.values())) if cartridge_hotset_layers else 0,'overlap_l2_read_compute':a.overlap_l2_read_compute,'overlap_pass_pattern':a.overlap_pass_pattern,'mapped_persistent_l2':a.mapped_persistent_l2,'pinned_verified_persistent_l2':a.pinned_verified_persistent_l2,'reusable_arena_persistent_l2':a.reusable_arena_persistent_l2,'mapped_l2_willneed':a.mapped_l2_willneed,'mapped_l2_parallel_prefault':a.mapped_l2_parallel_prefault,'inprocess_finish':a.inprocess_finish,'inprocess_attention':a.inprocess_attention,'inprocess_output':a.inprocess_output,'inmemory_layer_flow':a.inmemory_layer_flow,'activation_capture_dir':str(a.activation_capture_dir.resolve()) if a.activation_capture_dir else None,'capture_positions':sorted(capture_positions),'capture_layers':sorted(capture_layers),'shared_one_time_stage_seconds':shared_stage_seconds,'declared_streaming_cache_bytes':(expert_cache_bytes if a.resident_replay else 256*1024*1024),'declared_largest_native_arena_bytes':768*1024*1024,'quality_track':(expert_pool is not None and not a.exact_pool_escape_after_prompt) or a.continuation_active_experts != 4 or a.continuation_gate_mass_threshold is not None,'constrained_expert_pool_path':str(a.expert_pool.resolve()) if a.expert_pool else None,'constrained_expert_pool_canonical_sha256':expert_pool_sha,'constrained_expert_pool_preloaded':a.preload_expert_pool,'constrain_after_prompt':a.constrain_after_prompt,'exact_pool_escape_after_prompt':a.exact_pool_escape_after_prompt,'incremental_pool_admission':a.incremental_pool_admission,'constrained_expert_pool_preload_seconds':pool_preload_seconds,'constrained_expert_pool_preload_metrics':pool_preload_metrics,
                'claim_boundary':(('A token-conditioned sequence used per-layer rotated K/V history and traversed all 36 attention/MoE blocks for each token. Declared prompt tokens were teacher-forced before greedy continuation. This is exact repeatability evidence for the custom packed path, not yet chat-template quality validation or steady-state generation speed.' if a.token_count>1 else 'A token-conditioned position-zero sequence traversed embedding, all 36 attention/MoE blocks, final norm and vocabulary head to produce a finite repeatable argmax token. This is prompt-token execution evidence, not yet multi-token prompt quality validation or steady-state generation speed.') if forced_input_ids!=[BOS] else ('A BOS-conditioned greedy sequence used per-layer rotated K/V history and traversed all 36 attention/MoE blocks for each token. This is exact repeatability evidence for the custom packed path, not yet text-quality validation or steady-state generation speed.' if a.token_count>1 else 'A BOS-conditioned position-zero sequence traversed embedding, all 36 attention/MoE blocks, final norm and vocabulary head to produce a finite repeatable argmax token. This is first-token execution evidence, not yet text-quality validation or steady-state generation speed.'))}
        if a.exact_pool_escape_after_prompt:
            report['claim_boundary']=('The complete GPT-OSS 120B attention/residual backbone, unrestricted 128-expert router and original selected expert weights were executed at every position. A hash-bound protected pool served resident hits; any unrestricted winning expert outside the pool was fetched exactly from the verified SD warehouse. Such exceptions remain transient when the declared cache is full, or occupy only unprotected LRU capacity when an exception halo is declared; they can never evict the protected core. No router eligibility or neural mathematics was changed. Repeatability is measured against a second run; equivalence to a separately frozen unrestricted control requires explicit token, hidden-state and logit comparison.')
        elif expert_pool:
            report['claim_boundary']=('The complete GPT-OSS 120B attention/residual backbone and original expert weights were executed. '+('Prompt positions used unrestricted routing; only autoregressive continuation used the hash-bound resident pool. ' if a.constrain_after_prompt else 'Router eligibility was constrained to a hash-bound resident expert pool for all positions. ')+'Repeatability is measured only against a second candidate run. This is a changed-model quality track, not bit-exact unrestricted GPT-OSS 120B inference; semantic quality and genuine later-token speed require separate comparison with the frozen unrestricted control.')
        if cartridge_layers is not None:
            report['claim_boundary'] += ' The signed family cartridge changes only L2 eviction priority: it performs no eager SD reads and never changes router eligibility, expert values, gates, or fallback correctness.'
        report['canonical_sha256']=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:report[k] for k in ('status','input_token_id','generated_token_id','routes_repeatable','final_hidden_and_logits_bitwise_repeatable','canonical_sha256')},sort_keys=True))
if __name__=='__main__':main()
