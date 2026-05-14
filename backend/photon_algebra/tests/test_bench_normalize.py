def test_normalize_bench(benchmark):
    from backend.photon_algebra.rewriter import normalize
    expr = {"op":"⊕","states":["a",{"op":"★","state":"a"},"b"]}
    benchmark(lambda: normalize(expr))