#!/usr/bin/env python3
"""Isolate C4 addition order using a real, exact fourth contribution."""
from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore, ctypes_component_pointer_array
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical, digest, load, WIDTH


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--capture-stem', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('refusing to overwrite evidence')
    metadata, router, ffn, frozen_output = load(args.capture_stem)
    if len(metadata['route']) != 4:
        raise SystemExit('requires four original experts')
    store = GptOssExpertFrameStore(args.manifest, 256 * 1024 * 1024)
    values = store.get_layer_route_parallel(metadata['layer'], metadata['route'], workers=1)
    blobs = [value[projection][kind] for value in values for projection in ('gate', 'up', 'down') for kind in ('weight', 'bias')]
    refs, pointers = ctypes_component_pointer_array(blobs)
    refs4, pointers4 = ctypes_component_pointer_array(blobs[18:])
    gates = np.asarray([float(f'{value:.9g}') for value in metadata['gates']], dtype=np.float32)
    fp = ctypes.POINTER(ctypes.c_float)
    vp = ctypes.POINTER(ctypes.c_void_p)
    dp = ctypes.POINTER(ctypes.c_double)
    source = Path(__file__).parents[1] / 'modules/aion_inference/native/gptoss_persistent_moe_library.cpp'
    with tempfile.TemporaryDirectory(prefix='aion-c4-order-') as temporary:
        library_path = Path(temporary) / 'moe.dylib'
        subprocess.run(['clang++', '-std=c++17', '-O3', '-dynamiclib', '-I/opt/homebrew/include', str(source), '-L/opt/homebrew/lib', '-lggml', '-lggml-base', '-ldl', '-o', str(library_path)], check=True)
        library = ctypes.CDLL(str(library_path))
        full = library.aion_gptoss_moe_finish
        full.argtypes = [fp, fp, vp, fp, fp, ctypes.c_int, dp]
        active = library.aion_gptoss_moe_finish_active
        active.argtypes = [fp, fp, vp, fp, ctypes.c_int, fp, ctypes.c_int, dp]
        one = library.aion_gptoss_one_expert_contribution_batch
        one.argtypes = [fp, vp, fp, ctypes.c_int, fp, ctypes.c_int, dp]
        corrected = library.aion_gptoss_moe_finish_top3_correction
        corrected.argtypes = [fp, fp, vp, fp, fp, fp, ctypes.c_int, dp]
        elapsed = ctypes.c_double()
        reference, reduced, exact_c4, reordered, active4 = [np.empty(WIDTH, dtype=np.float32) for _ in range(5)]
        ptr = lambda value: value.ctypes.data_as(fp)
        calls = [lambda: full(ptr(ffn), ptr(router), pointers, ptr(gates), ptr(reference), 6, ctypes.byref(elapsed)),
                 lambda: active(ptr(ffn), ptr(router), pointers, ptr(gates), 4, ptr(active4), 6, ctypes.byref(elapsed)),
                 lambda: active(ptr(ffn), ptr(router), pointers, ptr(gates), 3, ptr(reduced), 6, ctypes.byref(elapsed)),
                 lambda: one(ptr(router), pointers4, ptr(gates[3:]), 1, ptr(exact_c4), 6, ctypes.byref(elapsed)),
                 lambda: corrected(ptr(ffn), ptr(router), pointers, ptr(gates), ptr(exact_c4), ptr(reordered), 6, ctypes.byref(elapsed))]
        for call in calls:
            status = call()
            if status:
                raise RuntimeError(f'native order gate failed: {status}')
    old = reduced + exact_c4
    acceptance = {'full_matches_frozen_capture': np.array_equal(reference, frozen_output),
                  'active4_matches_full': np.array_equal(active4, reference),
                  'correct_order_exact_c4_matches_full': np.array_equal(reordered, reference)}
    report = {'schema': 'aion.gptoss-120b-c4-reduction-order-gate.v1',
              'status': 'PASSED' if all(acceptance.values()) else 'FAILED',
              'acceptance': acceptance,
              'old_order_differing_elements': int(np.count_nonzero(old != reference)),
              'old_order_max_abs_error': float(np.max(np.abs(old - reference))),
              'correct_order_differing_elements': int(np.count_nonzero(reordered != reference)),
              'capture_metadata_sha256': digest(Path(f'{args.capture_stem}.json')),
              'native_source_sha256': digest(source),
              'claim_boundary': 'Real quartet arithmetic audit using the exact original E4 contribution, not an approximation or speed benchmark. Passing removes addition-order error only; it does not certify a learned correction.'}
    report['canonical_sha256'] = canonical(report)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
