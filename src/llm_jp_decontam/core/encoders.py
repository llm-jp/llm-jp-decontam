"""Conversion of a text into the sequence of units that n-grams are made of (--tokenizer)."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from .errors import DecontamError

UNIT_DTYPE = "<u4"

SEPARATOR = 0x110000
"""Unit placed between text elements.  It is larger than every Unicode code point, and every
token id must be smaller, so no n-gram can span two text elements."""


class Encoder(Protocol):
    """Turns texts into arrays of units (dtype UNIT_DTYPE)."""

    def encode_many(self, texts: list[str]) -> list[np.ndarray]: ...


class CharEncoder:
    """One unit per Unicode code point."""

    def encode_many(self, texts: list[str]) -> list[np.ndarray]:
        return [
            np.frombuffer(text.encode("utf-32-le", "surrogatepass"), dtype=UNIT_DTYPE)
            for text in texts
        ]


class SpmEncoder:
    """One unit per SentencePiece token (the token id).

    The normalization and the dummy prefix stored in the model file are applied as they are.
    """

    def __init__(self, model_path: str) -> None:
        import sentencepiece

        self._processor = sentencepiece.SentencePieceProcessor(model_file=model_path)
        if self._processor.get_piece_size() > SEPARATOR:
            raise DecontamError("the vocabulary of --tokenizer-model is too large")

    def encode_many(self, texts: list[str]) -> list[np.ndarray]:
        if not texts:
            return []
        # One thread, like the rest of the program: parallelism is left to the caller.
        token_ids = self._processor.encode(texts, num_threads=1)
        return [np.asarray(ids, dtype=UNIT_DTYPE) for ids in token_ids]


def make_encoder(tokenizer: str, model_path: str | None) -> Encoder:
    """Create the encoder for the values of --tokenizer and --tokenizer-model."""
    if tokenizer == "char":
        if model_path:
            raise DecontamError("--tokenizer-model is only used with --tokenizer spm")
        return CharEncoder()
    if tokenizer == "spm":
        if not model_path:
            raise DecontamError("--tokenizer spm needs --tokenizer-model")
        return SpmEncoder(model_path)
    raise DecontamError(f"unknown tokenizer: {tokenizer}")
