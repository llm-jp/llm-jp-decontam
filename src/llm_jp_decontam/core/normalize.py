"""Text normalizations selectable with --normalize."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable

Normalizer = Callable[[str], str]


def normalize_none(text: str) -> str:
    """Leave the text unchanged."""
    return text


def normalize_nfkc_lower_ws(text: str) -> str:
    """Apply NFKC, str.lower(), and replace every run of whitespace by one U+0020.

    Whitespace means the characters matched by the regular expression `\\s`, which are the
    characters that str.split() splits on.
    """
    if not text.isascii():
        text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    words = text.split()
    if not words:
        return " " if text else ""
    result = " ".join(words)
    if text[0].isspace():
        result = " " + result
    if text[-1].isspace():
        result += " "
    return result


NORMALIZERS: dict[str, Normalizer] = {
    "none": normalize_none,
    "nfkc-lower-ws": normalize_nfkc_lower_ws,
}
