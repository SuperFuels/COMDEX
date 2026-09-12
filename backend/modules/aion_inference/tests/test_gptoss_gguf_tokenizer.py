from backend.modules.aion_inference.gptoss_gguf_tokenizer import GptOssGGUFTokenizer


def test_bpe_and_harmony_wrapper() -> None:
    tokenizer = GptOssGGUFTokenizer(
        ["a", "b", "ab", "Ġ", "Ġa", "user", "assistant",
         "<|start|>", "<|message|>", "<|end|>"],
        ["a b", "Ġ a"],
    )
    assert tokenizer.encode("ab a") == [2, 4]
    assert tokenizer.harmony_user_prompt("ab a") == [7, 5, 8, 2, 4, 9, 7, 6]
