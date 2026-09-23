from backend.scripts.run_aion_mxfp4_block_layout_audit import audit


def test_installed_decoder_matches_planar_layout():
    report = audit()
    assert report['status'] == 'PASSED'
    assert (report['block_values'], report['block_bytes']) == (32, 17)
    assert all(c['planar_decode_bitwise_equal'] for c in report['cases'])
    assert not any(c['unrepacked_adjacent_decode_bitwise_equal'] for c in report['cases'])


def test_exponent_zero_is_not_zero_scale():
    case = audit()['cases'][0]
    assert case['exponent'] == 0
    assert case['f32_scale'] == 2. ** -127
