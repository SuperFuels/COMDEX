"""Run real-data chronological smoke probes while cross-family capture proceeds."""
import argparse
import json
from pathlib import Path
from backend.scripts.run_aion_ranked_correction_local_gate import chronological_sanity


def main():
    p=argparse.ArgumentParser();p.add_argument('--job',type=Path,required=True)
    p.add_argument('--corpus',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True)
    a=p.parse_args()
    for layer in (2,13,18):
        r=chronological_sanity(a.job,a.corpus,a.output_root/f'layer-{layer}',layer)
        print(json.dumps(r),flush=True)

if __name__=='__main__':
    main()
