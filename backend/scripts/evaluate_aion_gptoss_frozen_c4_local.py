#!/usr/bin/env python3
"""Prospective local evaluation of a frozen correction, without refitting."""
from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore, ctypes_component_pointer_array
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical, digest, load, WIDTH, ORIGINAL_EXPERT_BYTES
from backend.scripts.run_aion_gptoss_first_token_gate import local_c4_prediction, local_c4_similarity, local_c4_region_supported


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--cartridge', type=Path, required=True)
    parser.add_argument('--capture-dir', type=Path, required=True)
    parser.add_argument('--teacher-receipt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timing-samples', type=int, default=0,
                        help='Paired warmed timings including similarity, support check and prediction')
    args = parser.parse_args()
    if args.timing_samples < 0:
        raise SystemExit('timing sample count must be nonnegative')
    if args.output.exists():
        raise SystemExit('refusing to overwrite evidence')
    teacher = json.loads(args.teacher_receipt.read_text())
    body = dict(teacher)
    claimed = body.pop('canonical_sha256')
    if canonical(body) != claimed:
        raise SystemExit('teacher receipt hash mismatch')
    if teacher.get('status') != 'PASSED' or not teacher.get('routes_repeatable') or not teacher.get('final_hidden_and_logits_bitwise_repeatable'):
        raise SystemExit('teacher must pass exact repeatability before evaluation')
    if Path(teacher['activation_capture_dir']).resolve() != args.capture_dir.resolve():
        raise SystemExit('capture directory differs from teacher receipt')
    values = np.load(args.cartridge, allow_pickle=False)
    cartridge = {name: values[name].copy() for name in values.files}
    if str(cartridge['schema'].item()) not in ('aion.gptoss-120b-local-c4-cartridge.v1', 'aion.gptoss-120b-local-c4-cartridge.v2'):
        raise SystemExit('unknown correction schema')
    layer, expert = int(cartridge['layer']), int(cartridge['expert'])
    store = GptOssExpertFrameStore(args.manifest, 256 * 1024 * 1024)
    original = store.get_layer_route_parallel(layer, [expert], workers=1)[0]
    blobs = [original[projection][kind] for projection in ('gate', 'up', 'down') for kind in ('weight', 'bias')]
    references, pointers = ctypes_component_pointer_array(blobs)
    source = Path(__file__).parents[1] / 'modules/aion_inference/native/gptoss_persistent_moe_library.cpp'
    rows = []
    with tempfile.TemporaryDirectory(prefix='aion-frozen-c4-') as temporary:
        library = Path(temporary) / 'moe.dylib'
        subprocess.run(['clang++', '-std=c++17', '-O3', '-dynamiclib', '-I/opt/homebrew/include', str(source), '-L/opt/homebrew/lib', '-lggml', '-lggml-base', '-ldl', '-o', str(library)], check=True)
        function = ctypes.CDLL(str(library)).aion_gptoss_one_expert_contribution_batch
        function.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.POINTER(ctypes.c_double)]
        function.restype = ctypes.c_int
        for path in sorted(args.capture_dir.glob(f'position-*-layer-{layer}.json')):
            metadata, router, ffn, output = load(path.with_suffix(''))
            if len(metadata['route']) != 4:
                raise SystemExit('evaluation requires unrestricted four-expert captures')
            row = {'position': int(metadata['position']), 'metadata_sha256': digest(path), 'identity_match': metadata['route'][3] == expert, 'region_supported': False}
            if row['identity_match']:
                similarity = local_c4_similarity(router, ffn, cartridge)
                supported = similarity >= float(cartridge['minimum_joint_cosine']) and local_c4_region_supported(router, cartridge)
                row.update(joint_cosine=similarity, region_supported=bool(supported))
                if supported:
                    gate = np.asarray([metadata['gates'][3]], dtype=np.float32)
                    exact = np.empty(WIDTH, dtype=np.float32)
                    elapsed = ctypes.c_double()
                    status = function(router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers, gate.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 1, exact.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 6, ctypes.byref(elapsed))
                    if status:
                        raise RuntimeError(f'exact contribution failed: {status}')
                    started = time.perf_counter_ns()
                    predicted = local_c4_prediction(router, gate[0], cartridge)
                    row['correction_compute_ms'] = (time.perf_counter_ns() - started) / 1e6
                    error = float(np.linalg.norm(predicted.astype(np.float64) - exact.astype(np.float64)) / max(np.linalg.norm(output.astype(np.float64)), 1e-30))
                    row.update(relative_l2=error, local_accuracy_pass=error <= 0.02, exact_e4_compute_ms=elapsed.value)
                    if args.timing_samples:
                        def exact_call():
                            status = function(router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers, gate.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 1, exact.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 6, ctypes.byref(elapsed))
                            if status:
                                raise RuntimeError(f'exact timing call failed: {status}')
                        def correction_call():
                            if local_c4_similarity(router, ffn, cartridge) < float(cartridge['minimum_joint_cosine']) or not local_c4_region_supported(router, cartridge):
                                raise RuntimeError('frozen region changed during timing')
                            return local_c4_prediction(router, gate[0], cartridge)
                        for _ in range(5):
                            exact_call()
                            correction_call()
                        measurements = {'exact': [], 'correction': []}
                        for sample in range(args.timing_samples):
                            calls = [('exact', exact_call), ('correction', correction_call)]
                            for name, call in (calls if sample % 2 == 0 else calls[::-1]):
                                start = time.perf_counter_ns()
                                call()
                                measurements[name].append((time.perf_counter_ns() - start) / 1e6)
                        ratio = float(np.median(measurements['correction']) / max(np.median(measurements['exact']), 1e-30))
                        row.update(charged_correction_ms_p50=float(np.median(measurements['correction'])),
                                   charged_correction_ms_p95=float(np.percentile(measurements['correction'], 95)),
                                   warmed_exact_e4_ms_p50=float(np.median(measurements['exact'])),
                                   warmed_exact_e4_ms_p95=float(np.percentile(measurements['exact'], 95)),
                                   charged_correction_to_e4_p50_ratio=ratio,
                                   narrow_compute_cost_pass=ratio <= 0.25)
            rows.append(row)
    supported = [row for row in rows if row['region_supported']]
    passing = [row for row in supported if row['local_accuracy_pass']]
    cost_passing = [row for row in supported if row.get('narrow_compute_cost_pass', False)]
    boundaries = {}
    for path in sorted(args.capture_dir.glob('position-*-layer-*.json')):
        metadata = json.loads(path.read_text())
        if 'router_logits_sha256' not in metadata:
            continue
        score_path = Path(f'{path.with_suffix("")}-router_logits.bin')
        if digest(score_path) != metadata['router_logits_sha256']:
            raise SystemExit('router score capture hash mismatch')
        scores = np.fromfile(score_path, dtype='<f4')
        if scores.shape != (128,) or not np.isfinite(scores).all():
            raise SystemExit('invalid router score capture')
        order = np.argsort(scores, kind='stable')[::-1]
        margin = float(np.float64(scores[order[3]]) - np.float64(scores[order[4]]))
        boundaries.setdefault(str(metadata['layer']), []).append(margin)
    report = {'schema': 'aion.gptoss-120b-frozen-c4-local-evaluation.v1',
              'status': 'LOCAL_TRANSFER_REQUIRES_DOWNSTREAM_GATE' if supported and len(passing) == len(supported) and (not args.timing_samples or len(cost_passing) == len(supported)) else 'NOT_CERTIFIED',
              'created_at': datetime.now(timezone.utc).isoformat(), 'quality_track': True,
              'cartridge_sha256': digest(args.cartridge), 'teacher_canonical_sha256': claimed,
              'layer': layer, 'expert': expert, 'total_e4_calls': len(rows),
              'identity_matches': sum(row['identity_match'] for row in rows),
              'supported_calls': len(supported), 'local_accuracy_passes': len(passing),
              'charged_compute_cost_passes': len(cost_passing) if args.timing_samples else None,
              'supported_traffic_share': len(supported) / max(len(rows), 1),
              'cartridge_resident_array_bytes': sum(value.nbytes for value in cartridge.values()),
              'original_expert_declared_bytes': ORIGINAL_EXPERT_BYTES,
              'captured_router_boundary_margins': {key: {'positions': len(margins), 'min': min(margins), 'p50': float(np.median(margins)), 'p95': float(np.percentile(margins, 95))} for key, margins in boundaries.items()},
              'rows': rows, 'no_refitting': True, 'exact_e4_fallback_required': True,
              'timing_samples': args.timing_samples,
              'claim_boundary': 'Prospective local evaluation only. This trajectory belongs to the training split but was not used to fit this frozen candidate. No sealed holdout, downstream stability, complete correction economics or full-generation speed claim.'}
    report['canonical_sha256'] = canonical(report)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: report[key] for key in ('status', 'total_e4_calls', 'identity_matches', 'supported_calls', 'local_accuracy_passes', 'canonical_sha256')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
