"""Frozen 128-position adaptive ABBA extension; no broad semantic promotion."""
import json
import os
import argparse
from pathlib import Path
import subprocess
import sys
import statistics

from backend.scripts.run_aion_gptoss_c4_coverage_queue import run_guarded_capture
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical, digest


def save(path, body):
    body['canonical_sha256'] = canonical(body)
    with path.open('x') as handle:
        json.dump(body, handle, indent=2, sort_keys=True)


def signatures(run):
    return [(t['position'], t['input_token_id'], t['generated_token_id'],
             t['final_hidden_sha256'], t['logits_sha256'],
             [(l['layer'], l['route'], l['output_sha256']) for l in t['layers']])
            for t in run['tokens']]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token-count', type=int, default=128)
    parser.add_argument('--output-root', type=Path,
                        default=Path('results/aion_template_128_generation_gate_20260913'))
    args = parser.parse_args()
    if args.token_count < 64 or args.token_count > 256:
        raise SystemExit('token count outside predeclared 64--256 safety range')
    repo = Path.cwd()
    out = repo / args.output_root
    out.mkdir(exist_ok=False)
    source_path = repo / 'results/aion_gptoss_120b_public_reasoning_adaptive080_continuation6_pool_quietcpu_64token_gate_20260912.json'
    source = json.loads(source_path.read_text())
    source_body = dict(source)
    assert source_body.pop('canonical_sha256') == canonical(source_body)
    library = repo / 'results/aion_joined_template_projection_gate_20260913/joined.dylib'
    pool = Path(source['constrained_expert_pool_path'])
    save(out / 'fixed_plan.json', dict(order=['original', 'joined', 'joined', 'original'],
         total_positions=args.token_count, passes=2, threads=6, expert_cache_gib=8,
         gate_mass=.8, min_experts=2, source_sha256=digest(source_path),
         pool_sha256=digest(pool), library_sha256=digest(library),
         advancement=dict(bitwise_source_prefix=True, all_128_positions_repeatable=True,
                          all_conditions_match_original=True, warm_median_ratio_at_least=1.10),
         claim_boundary='Longer extension of one existing adaptive trajectory. '
         'No sealed holdout, unrestricted or general semantic quality claim.'))
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
    assert not any(k.startswith('AION_LOCAL_C4') or k in (
        'AION_SERIAL_ACTIVE_CONTRIBUTIONS', 'AION_TRAJECTORY_LOOP_GUARD',
        'AION_PRESERVE_TOP1_GATE_MASS', 'AION_PRESERVE_DROPPED_GATE_MASS') for k in env)
    reference = None
    results = []
    try:
        for index, mode in enumerate(('original', 'joined', 'joined', 'original'), 1):
            output = out / f'condition-{index}-{mode}.json'
            command = [sys.executable, '-u', '-m', 'backend.scripts.run_aion_gptoss_joined_projection_full_gate',
                '--projection-kernel', mode, '--joined-library', str(library),
                '--manifest', '/Volumes/AION_120B/AION-Warehouse/v1/expert-bank/gpt-oss-120b-q4km-expert-frames.v1/manifest.v1.json',
                '--output', str(output), '--threads', '6', '--resident-replay', '--expert-cache-gib', '8',
                '--inprocess-finish', '--inprocess-embedding', '--inprocess-attention', '--inprocess-output',
                '--inmemory-layer-flow', '--passes', '2', '--token-count', str(args.token_count),
                '--prompt-token-count', str(source['prompt_token_count']),
                '--input-token-ids', ','.join(map(str, source['input_token_ids'])),
                '--expert-pool', str(pool), '--preload-expert-pool', '--constrain-after-prompt',
                '--continuation-gate-mass-threshold', '.8', '--continuation-min-active-experts', '2',
                '--yield-mastery-curriculum']
            print('START', index, mode, flush=True)
            # Child owns the inference lease; never lock it in this parent too.
            with (out / f'condition-{index}.log').open('x') as log:
                # Guard helper manages disk reserve and preserves partial outputs.
                run_guarded_capture(command, repo, env, out, reserve_bytes=10*1024**3)
                log.write('guarded capture returned\n')
            actual = json.loads(output.read_text())
            body = dict(actual)
            assert body.pop('canonical_sha256') == canonical(body)
            assert actual['status'] == 'PASSED'
            assert actual['routes_repeatable'] and actual['final_hidden_and_logits_bitwise_repeatable']
            for label in ('run_a', 'run_b'):
                sig = signatures(actual[label])
                assert len(sig) == args.token_count
                assert sig[:64] == signatures(source[label])
                if reference is None:
                    reference = sig
                assert sig == reference
            tokens = [t for t in actual['run_b']['tokens'] if t['position'] >= source['prompt_token_count']]
            results.append(dict(condition=index, mode=mode, receipt_sha256=digest(output),
                                warm_continuation_tps=len(tokens)/sum(t['wall_seconds'] for t in tokens)))
            print('COMPLETE', index, mode, results[-1]['warm_continuation_tps'], flush=True)
        medians = {mode: statistics.median(r['warm_continuation_tps'] for r in results if r['mode'] == mode)
                   for mode in ('original', 'joined')}
        ratio = medians['joined']/medians['original']
        save(out / 'summary.json', dict(status='MECHANICAL_TIMING_GATE_PASS' if ratio >= 1.10 else 'NOT_PROMOTED',
             results=results, warm_median_tps=medians, candidate_over_control_ratio=ratio,
             claim_boundary=f'One adaptive {args.token_count}-position extension, all measured paths bitwise matched. '
             'Completed-answer semantic review remains separate; no unrestricted or general quality promotion.'))
    except Exception as exc:
        save(out / 'STOPPED.json', dict(status='STOPPED_PRESERVE_PARTIAL_ATTEMPTS',
             completed_conditions=results, error=repr(exc)))
        raise


if __name__ == '__main__':
    main()
