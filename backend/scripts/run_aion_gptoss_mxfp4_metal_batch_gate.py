#!/usr/bin/env python3
"""Find the CPU/Metal crossover for a real batched GPT-OSS expert."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--expert", type=int, default=0)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-metal-batch-") as temporary:
        root = Path(temporary); metal_exe, cpu_exe = root/"metal", root/"cpu"
        common=["clang++","-std=c++17","-O3","-I/opt/homebrew/include"]
        libs=["-L/opt/homebrew/lib","-lggml","-lggml-base","-ldl"]
        subprocess.run([*common,str(native/"gptoss_mxfp4_metal_probe.cpp"),*libs,"-o",str(metal_exe)],check=True)
        subprocess.run([*common,str(native/"gptoss_packed_expert_cpu_gate.cpp"),*libs,"-o",str(cpu_exe)],check=True)
        store=GptOssExpertFrameStore(args.manifest,64*1024*1024);value=store.get(args.layer,args.expert)
        components=[]
        for projection in ("gate","up","down"):
            for kind in ("weight","bias"):
                path=root/f"{projection}-{kind}.bin";path.write_bytes(value[projection][kind]);components.append(str(path))
        base=np.sin(np.arange(2880,dtype=np.float32)*np.float32(0.00390625))
        samples=[]
        for batch in (1,2,4,8,16,32):
            input_path=root/f"input-{batch}.bin";input_path.write_bytes(np.tile(base,batch).tobytes())
            cpu_output=root/f"cpu-{batch}.bin";metal_output=root/f"metal-{batch}.bin"
            env={**os.environ,"AION_BATCH":str(batch),"AION_INPUT_PATH":str(input_path),"AION_OUTPUT_PATH":str(cpu_output)}
            cpu=json.loads(subprocess.check_output([str(cpu_exe),*components,"8","8"],env=env,text=True))
            metal=json.loads(subprocess.run([str(metal_exe),str(input_path),*components,str(metal_output)],text=True,capture_output=True,check=True).stdout)
            reference=np.fromfile(cpu_output,dtype="<f4").astype(np.float64);candidate=np.fromfile(metal_output,dtype="<f4").astype(np.float64);delta=reference-candidate
            samples.append({"batch":batch,"cpu":cpu,"metal":metal,
                "cpu_activations_per_second":1000.0*batch/cpu["p50_ms"],
                "metal_activations_per_second":1000.0*batch/metal["warm_p50_ms"],
                "metal_speedup":cpu["p50_ms"]/metal["warm_p50_ms"],
                "relative_l2_error":float(np.linalg.norm(delta)/np.linalg.norm(reference)),
                "max_abs_error":float(np.abs(delta).max()),"argmax_equal":int(reference.argmax())==int(candidate.argmax())})
    qualifying=[sample for sample in samples if sample["batch"]>=4 and sample["metal_speedup"]>=1.15 and sample["relative_l2_error"]<=0.01]
    report={"schema":"aion.gptoss-mxfp4-metal-batch-gate.v1",
        "status":"ADVANCE_BATCHED_METAL" if qualifying else "NOT_PROMOTED",
        "created_at":datetime.now(timezone.utc).isoformat(),"model":"GPT-OSS 120B Q4_K_M/MXFP4",
        "layer":args.layer,"expert":args.expert,"samples":samples,"warehouse_metrics":store.metrics(),
        "gates":{"minimum_batch":4,"metal_speedup_at_least":1.15,"relative_l2_at_most":0.01},
        "claim_boundary":"One real expert over repeated synthetic activation rows. This measures a packed batch crossover, not autoregressive generation or speculative-token acceptance."}
    report["canonical_sha256"]=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":report["status"],"summary":[{"batch":x["batch"],"metal_speedup":x["metal_speedup"],"cpu_rate":x["cpu_activations_per_second"],"metal_rate":x["metal_activations_per_second"]} for x in samples],"canonical_sha256":report["canonical_sha256"]},sort_keys=True))


if __name__=="__main__":
    main()
