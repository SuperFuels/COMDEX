from backend.scripts.run_aion_template_long_generation_gate import signatures


def sample():
    return {'tokens': [{'position': 0, 'input_token_id': 10, 'generated_token_id': 11,
            'final_hidden_sha256': 'hidden', 'logits_sha256': 'logits',
            'wall_seconds': 3., 'layers': [{'layer': 0, 'route': [1, 2],
                                          'output_sha256': 'layer'}]}]}


def test_signatures_ignore_timing_only():
    a, b = sample(), sample()
    b['tokens'][0]['wall_seconds'] = 1.
    assert signatures(a) == signatures(b)


def test_signatures_detect_route_and_token_changes():
    a, b = sample(), sample()
    b['tokens'][0]['layers'][0]['route'] = [2, 1]
    assert signatures(a) != signatures(b)
    b = sample()
    b['tokens'][0]['generated_token_id'] = 12
    assert signatures(a) != signatures(b)
