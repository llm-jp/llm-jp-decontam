"""The statistics file: written by decontam-stats, read by decontam-filter.

A TSV with a header line and one row per pair of a data record and a reference record,
sorted by data_line and ref_line.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import NamedTuple

from .errors import DecontamError


class StatsRow(NamedTuple):
    """Overlap between one data record and one reference record."""

    data_line: int
    """Line number of the data record (0-based)."""
    data_id: str
    ref_line: int
    """Line number of the reference record (0-based)."""
    ref_id: str
    matched_ngrams: int
    """Number of distinct n-grams that occur in both records."""
    ref_ngrams: int
    """Number of distinct n-grams of the reference record."""
    data_ngrams: int
    """Number of distinct n-grams of the data record."""
    matched_short_texts: int
    """Number of distinct texts of the reference record, shorter than the n-gram length, that
    equal a whole text element of the data record."""

    def to_line(self) -> str:
        return "\t".join(map(str, self)) + "\n"


COLUMNS = StatsRow._fields
HEADER = "\t".join(COLUMNS) + "\n"


def read_stats(path: str) -> Iterator[StatsRow]:
    """Iterate over the rows of a statistics file."""
    with open(path, encoding="utf-8", newline="") as file:
        if file.readline() != HEADER:
            raise DecontamError(f"not a statistics file of decontam-stats (header): {path}")
        for line in file:
            cells = line.rstrip("\n").split("\t")
            if len(cells) != len(COLUMNS):
                raise DecontamError(f"malformed row in {path}: {line[:200]!r}")
            yield StatsRow(int(cells[0]), cells[1], int(cells[2]), cells[3], *map(int, cells[4:]))
