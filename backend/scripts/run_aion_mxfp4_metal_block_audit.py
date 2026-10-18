"""Run and preserve the bounded Metal representation gate, never a speed claim."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess

from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('refusing to overwrite evidence')
    source = Path('backend/modules/aion_inference/native/gptoss_mxfp4_metal_block_audit.mm')
    with Path('.runtime/aion-gptoss-inference.lock').open('a') as lease:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        cases = []
        for mode, extra in [('floating_scale', []), ('integer_bit_decode', ['--bit-decode'])]:
            result = subprocess.run([str(args.binary.resolve()), *extra],
                                    capture_output=True, text=True, timeout=60)
            cases.append(dict(mode=mode, exit_code=result.returncode,
                              report=json.loads(result.stdout), stderr=result.stderr))
    body = dict(schema='aion.mxfp4-metal-block-audit.v1', cases=cases,
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                binary_sha256=hashlib.sha256(args.binary.read_bytes()).hexdigest(),
                claim_boundary='Synthetic block decode only. Integer writes preserve '
                'subnormal bit patterns here; later Metal floating arithmetic can still '
                'flush subnormals. No actual expert scales, matvec, model or speed tested.')
    body['canonical_sha256'] = canonical(body)
    with args.output.open('x') as handle:
        json.dump(body, handle, indent=2, sort_keys=True)
    print(json.dumps(body), flush=True)
    if cases[1]['exit_code']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
