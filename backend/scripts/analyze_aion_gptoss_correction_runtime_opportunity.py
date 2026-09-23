"""Locate correction opportunity in completed runtime timings, without inference."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical, digest


def summarize_run(run: dict, prompt_positions: int, correction_ratio: float) -> dict:
    tokens = [t for t in run['tokens'] if t['position'] >= prompt_positions]
    if not tokens:
        raise ValueError('no continuation positions')
    wall = sum(float(t['wall_seconds']) for t in tokens)
    if not math.isfinite(wall) or wall <= 0:
        raise ValueError('invalid continuation wall time')
    counts = Counter()
    layers = defaultdict(lambda: {'calls': 0, 'four_expert_calls': 0,
                                 'finish_seconds': 0., 'delivery_seconds': 0.,
                                 'equal_share_e4_seconds': 0., 'equal_share_last_expert_seconds': 0.})
    for token in tokens:
        if len(token['layers']) != 36 or {l['layer'] for l in token['layers']} != set(range(36)):
            raise ValueError('continuation does not contain all 36 layers')
        for layer in token['layers']:
            n = len(layer['route'])
            if n not in (1, 2, 3, 4):
                raise ValueError('invalid active expert count')
            counts[n] += 1
            finish = float(layer['finish_process_seconds'])
            delivery = float(layer['expert_load_seconds'])
            if not all(math.isfinite(v) and v >= 0 for v in (finish, delivery)):
                raise ValueError('invalid component timing')
            entry = layers[layer['layer']]
            entry['calls'] += 1
            entry['finish_seconds'] += finish
            entry['delivery_seconds'] += delivery
            # Timings are aggregate. This attribution is hypothetical, not an
            # isolated E4 timing, and includes non-removable finish overhead.
            if n == 4:
                entry['four_expert_calls'] += 1
                entry['equal_share_e4_seconds'] += (finish + delivery) / 4
            if n >= 2:
                entry['equal_share_last_expert_seconds'] += (finish + delivery) / n
    e4 = sum(e['equal_share_e4_seconds'] for e in layers.values())
    last = sum(e['equal_share_last_expert_seconds'] for e in layers.values())

    def hypothetical(seconds):
        remaining = wall - seconds * (1 - correction_ratio)
        return wall / remaining if remaining > 0 else None

    return {'label': run.get('label'), 'continuation_positions': len(tokens),
            'continuation_seconds': wall, 'observed_window_tps': len(tokens) / wall,
            'active_expert_call_counts': dict(sorted(counts.items())),
            'four_expert_call_share': counts[4] / sum(counts.values()),
            'equal_share_e4_time_fraction': e4 / wall,
            'hypothetical_full_e4_coverage_multiplier': hypothetical(e4),
            'equal_share_last_expert_time_fraction': last / wall,
            'hypothetical_last_expert_replacement_multiplier': hypothetical(last),
            'layer_opportunity': [{'layer': layer, **entry} for layer, entry in
                                  sorted(layers.items(), key=lambda item: -item[1]['equal_share_e4_seconds'])]}


def analyze(path: Path, ratio: float = .0773) -> dict:
    if not math.isfinite(ratio) or not 0 <= ratio <= 1:
        raise ValueError('invalid correction ratio')
    source = json.loads(path.read_text())
    body = dict(source)
    if body.pop('canonical_sha256', None) != canonical(body):
        raise RuntimeError('source canonical hash mismatch')
    if source.get('status') != 'PASSED' or not source.get('routes_repeatable') or not source.get('final_hidden_and_logits_bitwise_repeatable'):
        raise RuntimeError('source lacks completed repeatable runs')
    runs = [source['run_a'], source['run_b'], *source.get('additional_runs', [])]
    report = {'schema': 'aion.correction-runtime-opportunity.v1',
              'source': str(path.resolve()), 'source_file_sha256': digest(path),
              'source_canonical_sha256': source['canonical_sha256'],
              'source_quality_track': source.get('quality_track'),
              'status': 'TIMING_OPPORTUNITY_ONLY',
              'resident_correction_ratio_assumption': ratio,
              'runs': [summarize_run(r, source['prompt_token_count'], ratio) for r in runs],
              'claim_boundary': 'No inference, fitting, certification, semantic validation or speed promotion. Aggregate route timing divided by active count assumes equal costs; resident correction ratio is not fault-path cost. Finish overhead, overlaps and locality make projections non-causal. Last-expert replacement for 2/3-expert calls requires new separately validated C2/C3 corrections, not the existing C4.'}
    report['canonical_sha256'] = canonical(report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.source)
    with args.output.open('x') as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(json.dumps({'canonical_sha256': report['canonical_sha256'], 'runs': [
        {k: r[k] for k in ('observed_window_tps', 'four_expert_call_share',
                           'hypothetical_full_e4_coverage_multiplier', 'hypothetical_last_expert_replacement_multiplier')}
        for r in report['runs']]}))


if __name__ == '__main__':
    main()
