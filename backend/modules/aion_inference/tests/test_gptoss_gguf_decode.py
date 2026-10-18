from backend.modules.aion_inference.gptoss_gguf_tokenizer import GptOssGGUFTokenizer, _byte_encoder


def test_decode_bpe_boundaries_and_whitespace():
    t = GptOssGGUFTokenizer(['a', 'b', 'Ġ', 'Ċ'], [])
    assert t.decode([0, 1, 2, 0, 3]) == 'ab a\n'


def test_decode_utf8_split_over_three_tokens():
    table = _byte_encoder()
    ids = list('€'.encode('utf-8'))
    t = GptOssGGUFTokenizer([table[value] for value in ids], [])
    assert t.decode([0, 1, 2]) == '€'


def test_decode_special_markers_optional():
    t = GptOssGGUFTokenizer(['a', '<|end|>', 'b'], [])
    assert t.decode([0, 1, 2]) == 'a<|end|>b'
    assert t.decode([0, 1, 2], include_special=False) == 'ab'


def test_decode_rejects_invalid_ids():
    t = GptOssGGUFTokenizer(['a'], [])
    for value in (-1, 1, True, 0.5):
        try:
            t.decode([value])
        except ValueError:
            pass
        else:
            raise AssertionError('invalid token ID accepted')
