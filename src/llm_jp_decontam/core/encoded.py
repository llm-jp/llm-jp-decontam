"""Layout of the unit sequences of many text elements in one array."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .arrays import ranges
from .encoders import SEPARATOR, UNIT_DTYPE


class EncodedTexts:
    """Unit sequences of text elements, laid out in one array and separated by SEPARATOR.

    A window that spans two elements contains SEPARATOR, so it equals no n-gram and no short
    text.  `starts`, `lengths` and `owners` have one entry per text element: its position in
    `units`, its number of units and the line number of its record.
    """

    def __init__(self, sequences: list[np.ndarray], owners: Sequence[int]) -> None:
        self.owners = np.asarray(owners, dtype=np.int64)
        self.lengths = np.array([sequence.size for sequence in sequences], dtype=np.int64)
        self.starts = np.cumsum(self.lengths + 1) - (self.lengths + 1)
        size = max(0, int(self.lengths.sum()) + len(sequences) - 1)
        self.units = np.full(size, SEPARATOR, dtype=UNIT_DTYPE)
        for sequence, start in zip(sequences, self.starts.tolist(), strict=True):
            self.units[start : start + sequence.size] = sequence

    def text_at(self, positions: np.ndarray) -> np.ndarray:
        """Index of the text element that contains each position."""
        return np.searchsorted(self.starts, positions, side="right") - 1

    def windows(self, length: int, selected: np.ndarray | None = None) -> tuple[np.ndarray, ...]:
        """Every window of `length` units that lies inside one text element.

        Returns (positions, texts): the start of each window in `units` and the index of its
        text element, ordered by text element and position.  `selected` (a boolean mask over
        the text elements) restricts the windows to these elements.
        """
        long_enough = self.lengths >= length
        if selected is not None:
            long_enough &= selected
        texts = np.nonzero(long_enough)[0]
        counts = self.lengths[texts] - length + 1
        return ranges(self.starts[texts], counts), np.repeat(texts, counts)
