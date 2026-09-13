"""Bounded installed-GGML block ABI check; no neural or GPU benchmark."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import struct

from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical


def audit():
    decode_type = ctypes.CFUNCTYPE(None, ctypes.c_void_p,
                                  ctypes.POINTER(ctypes.c_float), ctypes.c_int64)

    class Traits(ctypes.Structure):
        _fields_ = [('name', ctypes.c_char_p), ('block', ctypes.c_int64),
                    ('interleave', ctypes.c_int64), ('size', ctypes.c_size_t),
                    ('quantized', ctypes.c_bool), ('decode', decode_type),
                    ('encode', ctypes.c_void_p)]

    library_path = Path('/opt/homebrew/lib/libggml-base.dylib')
    library = ctypes.CDLL(str(library_path))
    library.ggml_get_type_traits.argtypes = [ctypes.c_int]
    library.ggml_get_type_traits.restype = ctypes.POINTER(Traits)
    traits = library.ggml_get_type_traits(39).contents
    if traits.name != b'mxfp4' or traits.block != 32 or traits.size != 17:
        raise RuntimeError('installed MXFP4 ABI differs from declared audit')
    grid = [0., .5, 1., 1.5, 2., 3., 4., 6.,
            0., -.5, -1., -1.5, -2., -3., -4., -6.]
    results = []
    for exponent in (0, 1, 100, 127, 200):
        packed_codes = bytes(i | ((15 - i) << 4) for i in range(16))
        raw = ctypes.create_string_buffer(bytes([exponent]) + packed_codes)
        actual = (ctypes.c_float * 32)()
        traits.decode(raw, actual, 32)
        scale = 2. ** (exponent - 127)
        expected = [grid[i] * scale for i in range(16)]
        expected += [grid[15 - i] * scale for i in range(16)]
        expected_bytes = struct.pack('<32f', *expected)
        actual_bytes = bytes(actual)
        adjacent = [grid[n] * scale for b in packed_codes
                    for n in (b & 15, b >> 4)]
        results.append({'exponent': exponent,
                        'planar_decode_bitwise_equal': actual_bytes == expected_bytes,
                        'unrepacked_adjacent_decode_bitwise_equal':
                        actual_bytes == struct.pack('<32f', *adjacent),
                        'f32_scale': struct.unpack('<f', struct.pack('<f', scale))[0]})
    report = {'schema': 'aion.mxfp4-block-layout-audit.v1',
              'status': 'PASSED' if all(r['planar_decode_bitwise_equal'] for r in results) else 'FAILED',
              'block_values': traits.block, 'block_bytes': traits.size,
              'library_sha256': hashlib.sha256(library_path.read_bytes()).hexdigest(),
              'cases': results,
              'claim_boundary': 'Installed CPU dequantizer block-layout check only. '
              'No Metal execution, expert arithmetic, performance or model-quality claim. '
              'GGML stores low nibbles in positions 0..15 and high nibbles in 16..31; '
              'existing split Metal probes explicitly repack them to adjacent order. '
              'Exponent zero needs special handling if a shader uses exponent bits directly.'}
    report['canonical_sha256'] = canonical(report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('refusing to overwrite evidence')
    report = audit()
    with args.output.open('x') as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
    print(json.dumps(report), flush=True)
    if report['status'] != 'PASSED':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
