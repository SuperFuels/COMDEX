"""Bounded local GPT-OSS tokenizer reconstructed from verified GGUF metadata."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import regex

from .expert_frame_gguf_reader import ExpertFrameGGUFReader
from .gguf_stream_index import read_gguf_stream_index


_PATTERN = regex.compile(
    r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*"
    r"[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?|"
    r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+"
    r"[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?|"
    r"\p{N}{1,3}| ?[^\s\p{L}\p{N}]+[\r\n/]*|\s*[\r\n]+|\s+(?!\S)|\s+"
)


def _byte_encoder() -> dict[int, str]:
    values = list(range(ord("!"), ord("~") + 1))
    values += list(range(ord("¡"), ord("¬") + 1))
    values += list(range(ord("®"), ord("ÿ") + 1))
    encoded = values[:]
    extra = 0
    for value in range(256):
        if value not in values:
            values.append(value)
            encoded.append(256 + extra)
            extra += 1
    return dict(zip(values, map(chr, encoded), strict=True))


class GptOssGGUFTokenizer:
    """Minimal exact BPE encoder for the gpt-4o tokenizer embedded in GGUF."""

    def __init__(self, tokens: list[str], merges: list[str]) -> None:
        self.tokens = tokens
        self.vocabulary = {token: index for index, token in enumerate(tokens)}
        self.ranks = {tuple(value.split(" ", 1)): rank
                      for rank, value in enumerate(merges)}
        self.byte_encoder = _byte_encoder()
        self.special = {token: index for index, token in enumerate(tokens)
                        if token.startswith("<|") and token.endswith("|>")}

    @classmethod
    def from_warehouse(cls, manifest: Path, cache_mib: int = 32) -> "GptOssGGUFTokenizer":
        source = __import__("json").loads(manifest.read_text())["verified_sources"][0]
        reader = ExpertFrameGGUFReader(
            manifest, source["name"], cache_bytes=cache_mib * 1024 * 1024,
        )
        metadata = read_gguf_stream_index(
            reader, int(source["size"]),
            {"tokenizer.ggml.model", "tokenizer.ggml.pre",
             "tokenizer.ggml.tokens", "tokenizer.ggml.merges"},
        )["metadata"]
        if metadata.get("tokenizer.ggml.model") != "gpt2":
            raise ValueError("unsupported tokenizer model")
        if metadata.get("tokenizer.ggml.pre") != "gpt-4o":
            raise ValueError("unsupported tokenizer preprocessor")
        return cls(metadata["tokenizer.ggml.tokens"], metadata["tokenizer.ggml.merges"])

    @lru_cache(maxsize=65536)
    def _bpe(self, value: str) -> tuple[str, ...]:
        parts = tuple(value)
        while len(parts) > 1:
            pairs = {(parts[index], parts[index + 1])
                     for index in range(len(parts) - 1)}
            pair = min(pairs, key=lambda item: self.ranks.get(item, 1 << 60))
            if pair not in self.ranks:
                break
            merged = []
            index = 0
            while index < len(parts):
                if index + 1 < len(parts) and parts[index:index + 2] == pair:
                    merged.append(parts[index] + parts[index + 1])
                    index += 2
                else:
                    merged.append(parts[index])
                    index += 1
            parts = tuple(merged)
        return parts

    def encode(self, text: str) -> list[int]:
        result = []
        for piece in _PATTERN.findall(text):
            encoded = "".join(self.byte_encoder[value] for value in piece.encode("utf-8"))
            for token in self._bpe(encoded):
                result.append(self.vocabulary[token])
        return result

    def harmony_user_prompt(self, text: str) -> list[int]:
        return [
            self.special["<|start|>"], self.vocabulary["user"],
            self.special["<|message|>"], *self.encode(text),
            self.special["<|end|>"], self.special["<|start|>"],
            self.vocabulary["assistant"],
        ]

    def decode(self, token_ids: list[int], include_special: bool = True) -> str:
        """Decode byte-BPE across token boundaries, preserving Harmony markers."""
        inverse = {character: value for value, character in self.byte_encoder.items()}
        pending = bytearray()
        parts = []

        def flush() -> None:
            if pending:
                parts.append(pending.decode('utf-8', errors='replace'))
                pending.clear()

        for token_id in token_ids:
            if not isinstance(token_id, int) or isinstance(token_id, bool):
                raise ValueError('token ID must be an integer')
            if token_id < 0 or token_id >= len(self.tokens):
                raise ValueError('token ID outside vocabulary')
            token = self.tokens[token_id]
            if token in self.special:
                flush()
                if include_special:
                    parts.append(token)
            else:
                pending.extend(inverse[character] for character in token)
        flush()
        return ''.join(parts)
