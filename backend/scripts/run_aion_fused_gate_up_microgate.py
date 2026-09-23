"""Numerical gate for one real packed expert; no generation or timing claim."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--capture-stem', type=Path, required=True)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--output-root', type=Path, required=True)
    p.add_argument('--matched-dot-input', action='store_true')
    p.add_argument('--timing', action='store_true')
    p.add_argument('--integer-dot', action='store_true')
    p.add_argument('--tiled-dot', action='store_true')
    args = p.parse_args()
    if shutil.disk_usage('.').free < 3 * 1024**3:
        raise SystemExit('3 GiB disk reserve')
    args.output_root.mkdir(exist_ok=False)
    with Path('.runtime/aion-gptoss-inference.lock').open('a') as lease:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        meta_path = args.capture_stem.with_suffix('.json')
        meta = json.loads(meta_path.read_text())
        layer = meta['layer']
        expert = meta['route'][0]
        store = GptOssExpertFrameStore(args.manifest, 16 * 1024**2)
        value = store.get(layer, expert)  # original component hashes verified by store
        activation = Path(f'{args.capture_stem}-router.bin')
        paths = []
        hashes = {}
        for name, data in [('input', activation.read_bytes()),
                           ('gate', value['gate']['weight']),
                           ('up', value['up']['weight']),
                           ('gate_bias', value['gate']['bias']),
                           ('up_bias', value['up']['bias'])]:
            path = args.output_root / f'{name}.bin'
            with path.open('xb') as handle:
                handle.write(data)
            hashes[name] = hashlib.sha256(data).hexdigest()
            paths.append(str(path.resolve()))
        extra = ['--matched-dot-input'] if args.matched_dot_input else []
        if args.timing:
            extra.append('--timing')
        if args.integer_dot:
            extra.append('--integer-dot')
        if args.tiled_dot:
            extra.append('--tiled-dot')
        result = subprocess.run([str(args.binary.resolve()), *paths, *extra],
                                capture_output=True, text=True, timeout=120)
        with (args.output_root / 'stdout.txt').open('x') as handle:
            handle.write(result.stdout)
        with (args.output_root / 'stderr.txt').open('x') as handle:
            handle.write(result.stderr)
        numerical = json.loads(result.stdout) if result.returncode == 0 else None
        body = dict(layer=layer, expert=expert, input_hashes=hashes,
                    native_source_sha256=hashlib.sha256(Path(
                        'backend/modules/aion_inference/native/gptoss_fused_gate_up_microgate.mm').read_bytes()).hexdigest(),
                    wrapper_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    capture_metadata_sha256=hashlib.sha256(meta_path.read_bytes()).hexdigest(),
                    binary_sha256=hashlib.sha256(args.binary.read_bytes()).hexdigest(),
                    manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                    returncode=result.returncode, numerical=numerical,
                    store_metrics=store.metrics(),
                    status=('EXACT_NUMERICAL_PASS' if numerical and all(
                        s['bitwise_mismatches'] == 0 for s in numerical['stages'])
                        else 'CHANGED_ARITHMETIC_NOT_PROMOTED'),
                    claim_boundary='One authentic activation and original expert, '
                    'gate/up+bias+SwiGLU comparison. Optional charged kernel timing '
                    'is not generation speed; no teacher token comparison or injection.')
        body['canonical_sha256'] = canonical(body)
        with (args.output_root / 'numerical_gate.json').open('x') as handle:
            json.dump(body, handle, indent=2, sort_keys=True)
        print(json.dumps(body), flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
