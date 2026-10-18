#!/usr/bin/env python3
"""Continuously capture training-only C4 trajectories in family-balanced order."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical, digest


def training_order(rows: list[dict]) -> list[dict]:
    families = sorted({row['family'] for row in rows if row['split'] == 'training'})
    groups = {family: [row for row in rows if row['split'] == 'training' and row['family'] == family] for family in families}
    return [groups[family][index] for index in range(max(map(len, groups.values()), default=0)) for family in families if index < len(groups[family])]


def run_guarded_capture(command: list[str], repository: Path, env: dict,
                        evidence_root: Path, reserve_bytes: int = 3 * 1024**3,
                        poll_seconds: float = 5.0) -> None:
    """Check disk reserve during a capture, not just between captures."""
    process = subprocess.Popen(command, cwd=repository, env=env)
    try:
        while process.poll() is None:
            if shutil.disk_usage(evidence_root).free < reserve_bytes:
                raise RuntimeError('local evidence reserve exhausted during capture; partial data preserved')
            time.sleep(poll_seconds)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command)
    finally:
        # Interrupt first so the inference-priority lease can unwind normally.
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def verify_capture(receipt: dict, capture_dir: Path, expected: int) -> None:
    body = dict(receipt)
    claimed = body.pop('canonical_sha256', None)
    if claimed != canonical(body) or receipt.get('status') != 'PASSED' or receipt.get('quality_track') or not receipt.get('routes_repeatable') or not receipt.get('final_hidden_and_logits_bitwise_repeatable'):
        raise RuntimeError('teacher capture did not pass bound exact repeatability')
    if len(list(capture_dir.glob('position-*-layer-*.json'))) != expected:
        raise RuntimeError('teacher capture observation count is incomplete')
    if Path(receipt['activation_capture_dir']).resolve() != capture_dir.resolve():
        raise RuntimeError('teacher capture directory differs from receipt')
    expected_addresses = {(position, layer) for position in receipt['capture_positions'] for layer in range(36)}
    observed = set()
    for path in capture_dir.glob('position-*-layer-*.json'):
        metadata = json.loads(path.read_text())
        if len(metadata.get('route', [])) != 4:
            raise RuntimeError('teacher must retain all four experts')
        address = (metadata['position'], metadata['layer'])
        if path.name != f'position-{address[0]}-layer-{address[1]}.json' or address not in expected_addresses:
            raise RuntimeError('capture address differs from declared full-layer grid')
        observed.add(address)
        for name in ('router', 'ffn', 'output', 'residual', 'router_logits', 'fourth_contribution'):
            binary = Path(f'{path.with_suffix("")}-{name}.bin')
            expected_bytes = 512 if name == 'router_logits' else 11520
            if not binary.exists() or binary.stat().st_size != expected_bytes or digest(binary) != metadata.get(f'{name}_sha256'):
                raise RuntimeError(f'capture binary failed verification: {binary}')
        # Earlier sealed captures retain only E4. New captures retain E2/E3
        # too; enforce hashes and the complete pair whenever either is declared.
        optional_names=('second_contribution','third_contribution')
        if any(f'{name}_sha256' in metadata for name in optional_names):
            for name in optional_names:
                binary=Path(f'{path.with_suffix("")}-{name}.bin')
                if not binary.exists() or binary.stat().st_size!=11520 or digest(binary)!=metadata.get(f'{name}_sha256'):
                    raise RuntimeError(f'ranked correction target failed verification: {binary}')
    if observed != expected_addresses:
        raise RuntimeError('capture grid is incomplete')
    for position in receipt['capture_positions']:
        vocabulary = capture_dir / f'position-{position}-vocabulary.bin'
        token = receipt['run_a']['tokens'][position]
        if not vocabulary.exists() or vocabulary.stat().st_size != 201088 * 4 or digest(vocabulary) != token['logits_sha256']:
            raise RuntimeError('full vocabulary capture differs from bound teacher logits')


def seal_completion(job: Path, row: dict, corpus: dict, receipt: dict, expected: int) -> None:
    capture_dir = job / 'captures'
    files = [{'name': path.name, 'sha256': digest(path), 'bytes': path.stat().st_size} for path in sorted(capture_dir.iterdir()) if path.is_file()]
    path = job / 'COMPLETE_VERIFIED.json'
    if path.exists():
        completion = json.loads(path.read_text())
        body = dict(completion)
        if body.pop('canonical_sha256', None) != canonical(body) or completion['capture_files'] != files or completion['corpus_canonical_sha256'] != corpus['canonical_sha256'] or completion['teacher_canonical_sha256'] != receipt['canonical_sha256']:
            raise RuntimeError('existing coverage completion sidecar failed verification')
        return
    completion = {'schema': 'aion.gptoss-c4-coverage-completion.v1',
                  'capture_id': row['capture_id'], 'split': 'training',
                  'corpus_canonical_sha256': corpus['canonical_sha256'],
                  'teacher_canonical_sha256': receipt['canonical_sha256'],
                  'expected_observations': expected, 'capture_files': files,
                  'claim_boundary': 'Bound authentic training trajectory only. No correction training, selection/holdout consumption, semantic promotion or speed claim.'}
    completion['canonical_sha256'] = canonical(completion)
    path.write_text(json.dumps(completion, indent=2, sort_keys=True) + '\n')
    print(f"COMPLETE_VERIFIED {row['capture_id']} sha256={completion['canonical_sha256']}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--maximum-captures', type=int, default=6)
    parser.add_argument('--persistent-l2-root', type=Path)
    parser.add_argument('--persistent-l2-gib', type=float, default=20)
    args = parser.parse_args()
    repository = Path(__file__).parents[2]
    if not args.root.resolve().is_relative_to((repository / 'results').resolve()):
        raise SystemExit('coverage evidence must remain in local repository results, not on SD')
    if args.maximum_captures < 1 or args.persistent_l2_gib <= 0:
        raise SystemExit('capture count and cache capacity must be positive')
    corpus = json.loads(args.corpus.read_text())
    body = dict(corpus)
    if body.pop('canonical_sha256', None) != canonical(body):
        raise SystemExit('corpus canonical hash mismatch')
    if corpus['warehouse_manifest_sha256'] != digest(args.manifest):
        raise SystemExit('corpus targets a different warehouse')
    args.root.mkdir(parents=True, exist_ok=True)
    required_free = 3 * 1024**3 + (int(args.persistent_l2_gib * 1024**3) if args.persistent_l2_root else 0)
    if shutil.disk_usage(args.root).free < required_free:
        raise SystemExit('insufficient local free space for declared coverage/cache programme')
    env = dict(os.environ)
    # Teacher collection must not inherit any experimental correction or
    # hidden diagnostic policy from the launching shell.
    if any(name.startswith('AION_LOCAL_C4') or name in ('AION_SERIAL_ACTIVE_CONTRIBUTIONS', 'AION_TRAJECTORY_LOOP_GUARD', 'AION_PRESERVE_TOP1_GATE_MASS', 'AION_PRESERVE_DROPPED_GATE_MASS') for name in env):
        raise SystemExit('teacher queue requires a clean changed-arithmetic environment')
    selected = training_order(corpus['rows'])[:args.maximum_captures]
    for row in selected:
        if shutil.disk_usage(args.root).free < 3 * 1024**3:
            raise SystemExit('local evidence reserve exhausted; preserving completed captures')
        job = args.root / row['capture_id']
        receipt_path = job / 'teacher.json'
        capture_dir = job / 'captures'
        expected = len(row['capture_positions']) * 36
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            verify_capture(receipt, capture_dir, expected)
            seal_completion(job, row, corpus, receipt, expected)
            print(f"SKIP_VERIFIED {row['capture_id']}", flush=True)
            continue
        if job.exists():
            raise SystemExit(f"preserved incomplete job requires inspection: {job}")
        job.mkdir()
        command = [sys.executable, '-m', 'backend.scripts.run_aion_gptoss_first_token_gate',
                   '--manifest', str(args.manifest), '--output', str(receipt_path),
                   '--threads', '6', '--resident-replay', '--expert-cache-gib', '8',
                   '--inprocess-finish', '--inprocess-embedding', '--inprocess-attention',
                   '--inprocess-output', '--inmemory-layer-flow', '--passes', '2',
                   '--token-count', str(row['token_count']), '--prompt-token-count', str(row['prompt_token_count']),
                   '--input-token-ids', ','.join(map(str, row['input_token_ids'])),
                   '--activation-capture-dir', str(capture_dir),
                   '--capture-positions', ','.join(map(str, row['capture_positions'])),
                   '--capture-layers', ','.join(map(str, range(36))), '--capture-counterfactuals',
                   '--yield-mastery-curriculum']
        if args.persistent_l2_root:
            command += ['--persistent-l2-root', str(args.persistent_l2_root),
                        '--persistent-l2-gib', str(args.persistent_l2_gib),
                        '--reusable-arena-persistent-l2', '--l2-admission-touches', '3']
        print(f"START_TRAINING_ONLY {row['capture_id']} expected_observations={expected}", flush=True)
        run_guarded_capture(command, repository, env, args.root)
        receipt = json.loads(receipt_path.read_text())
        verify_capture(receipt, capture_dir, expected)
        seal_completion(job, row, corpus, receipt, expected)
    print('TRAINING_QUEUE_COMPLETE', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
