"""Verified training coverage and explicitly hypothetical C4 speed economics.

Identity recurrence is not activation recurrence, accuracy or certification.
This report never consumes partial captures or selection/holdout data.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

from backend.scripts.run_aion_gptoss_c4_coverage_queue import verify_capture
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical, digest


def speed_bound(coverage: float, correction_cost: float, e4_time_share: float,
                baseline_tps: float = 7.0) -> dict:
    values = (coverage, correction_cost, e4_time_share, baseline_tps)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('economics must be finite')
    if not all(0 <= v <= 1 for v in values[:3]) or baseline_tps <= 0:
        raise ValueError('invalid economics domain')
    saved = coverage * e4_time_share * (1 - correction_cost)
    multiplier = 1 / (1 - saved) if saved < 1 else None
    return {'coverage_assumption': coverage, 'correction_cost_fraction_assumption': correction_cost,
            'e4_total_time_share_assumption': e4_time_share,
            'saved_total_time_fraction': saved, 'speed_multiplier_bound': multiplier,
            'hypothetical_tps_bound': baseline_tps * multiplier if multiplier is not None else None,
            'claim': 'Hypothetical Amdahl bound, not measured speed; excludes new overhead and locality regressions.'}


def summarize(root: Path, corpus_path: Path, minimum_support: int = 8) -> dict:
    if minimum_support < 1:
        raise ValueError('minimum support must be positive')
    corpus = json.loads(corpus_path.read_text())
    body = dict(corpus)
    if body.pop('canonical_sha256', None) != canonical(body):
        raise RuntimeError('corpus hash mismatch')
    rows = {row['capture_id']: row for row in corpus['rows'] if row['split'] == 'training'}
    counts = Counter()
    families: dict[tuple[int, int], Counter] = {}
    verified = []
    for sidecar in sorted(root.glob('*/COMPLETE_VERIFIED.json')):
        seal = json.loads(sidecar.read_text())
        body = dict(seal)
        if body.pop('canonical_sha256', None) != canonical(body):
            raise RuntimeError('completion hash mismatch')
        capture_id = sidecar.parent.name
        if capture_id not in rows or seal['capture_id'] != capture_id or seal['split'] != 'training':
            raise RuntimeError('completion is not declared training data')
        if seal['corpus_canonical_sha256'] != corpus['canonical_sha256']:
            raise RuntimeError('completion targets different corpus')
        row = rows[capture_id]
        directory = sidecar.parent / 'captures'
        receipt = json.loads((sidecar.parent / 'teacher.json').read_text())
        expected = len(row['capture_positions']) * 36
        verify_capture(receipt, directory, expected)
        files = [{'name': p.name, 'sha256': digest(p), 'bytes': p.stat().st_size}
                 for p in sorted(directory.iterdir()) if p.is_file()]
        if seal['capture_files'] != files or seal['teacher_canonical_sha256'] != receipt['canonical_sha256'] or seal['expected_observations'] != expected:
            raise RuntimeError('completion contents differ from evidence')
        for path in sorted(directory.glob('position-*-layer-*.json')):
            meta = json.loads(path.read_text())
            # Continuation only: prefill recurrence cannot establish decode savings.
            if meta['position'] < row['prompt_token_count']:
                continue
            key = (meta['layer'], meta['route'][3])
            counts[key] += 1
            families.setdefault(key, Counter())[row['family']] += 1
        verified.append({'capture_id': capture_id, 'completion_sha256': seal['canonical_sha256']})
    total = sum(counts.values())
    supported = sum(n for key, n in counts.items() if n >= minimum_support and len(families[key]) >= 2)
    pairs = [{'layer': key[0], 'expert': key[1], 'continuation_calls': n,
              'family_counts': dict(sorted(families[key].items())),
              'identity_support_only': n >= minimum_support and len(families[key]) >= 2}
             for key, n in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]
    report = {'schema': 'aion.c4-coverage-economics.v1',
              'status': 'VERIFIED_TRAINING_COVERAGE' if verified else 'WAITING_FOR_VERIFIED_CAPTURE',
              'corpus_canonical_sha256': corpus['canonical_sha256'],
              'verified_captures': verified,
              'partial_capture_directories_excluded': [p.name for p in sorted(root.iterdir()) if p.is_dir() and not (p / 'COMPLETE_VERIFIED.json').exists()],
              'continuation_e4_calls': total, 'minimum_identity_support': minimum_support,
              'cross_family_supported_identity_calls': supported,
              'cross_family_supported_identity_share': supported / total if total else None,
              'layer_expert_support': pairs,
              'certified_traffic_share': None,
              'hypothetical_equal_four_expert_cost_bounds': [speed_bound(c, .0773, .25) for c in (0.025, .1, .3, .5, 1)],
              'claim_boundary': 'No certification or speed promotion. Repeated identity does not prove local activation support. Equal expert costs and 7 t/s baseline are illustrative, not a matched runtime measurement.'}
    report['canonical_sha256'] = canonical(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--minimum-support', type=int, default=8)
    args = parser.parse_args()
    report = summarize(args.root, args.corpus, args.minimum_support)
    # Evidence is append-only; reserve the exact destination before writing.
    with args.output.open('x') as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(json.dumps({k: report[k] for k in ('status', 'continuation_e4_calls', 'certified_traffic_share', 'canonical_sha256')}))


if __name__ == '__main__':
    main()
