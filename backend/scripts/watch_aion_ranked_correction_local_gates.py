"""Run narrow local probes as authentic completed training jobs arrive."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--corpus',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--maximum-seconds',type=int,default=14400);a=p.parse_args()
    deadline=time.monotonic()+a.maximum_seconds
    corpus=json.loads(a.corpus.read_text())
    families={r['capture_id']:r['family'] for r in corpus['rows'] if r['split']=='training'}
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1')
    while time.monotonic()<deadline:
        jobs=sorted(path.parent for path in a.root.glob('*/COMPLETE_VERIFIED.json'))
        # Adjacent completed prompts define separate fitting/development probes.
        # No repeated development-driven policy tuning or sealed holdout access.
        for tr,dev in zip(jobs,jobs[1:]):
            if tr.name not in families or dev.name not in families:
                raise RuntimeError('watcher refuses non-training prompts')
            if families[tr.name]==families[dev.name]:
                continue
            dest=a.output_root/f'{tr.name}--{dev.name}'
            if dest.exists():
                if not (dest/'report.json').exists():
                    raise RuntimeError(f'incomplete local probe preserved: {dest}')
                continue
            print(f'START_LOCAL_GATE {tr.name} -> {dev.name}',flush=True)
            subprocess.run([sys.executable,'-m','backend.scripts.run_aion_ranked_correction_local_gate',
                            '--training-job',str(tr),'--development-job',str(dev),'--corpus',str(a.corpus),
                            '--output-directory',str(dest)],env=env,check=True)
        time.sleep(15)

if __name__=='__main__':
    main()
