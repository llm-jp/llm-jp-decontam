"""Computation of the overlap statistics between a data file and a reference index.

Every text element (the `content` or the `reasoning` of one message) is normalized and turned
into a sequence of units: Unicode code points or SentencePiece tokens.  An n-gram is a run of
`ngram_length` units inside one text element.  A text element of a reference record with fewer
units, at least one unit and at least one non-whitespace character is a short text.

A data record and a reference record form a pair when
  - they share at least one n-gram, or
  - a short text of the reference record equals a whole text element of the data record.
`write_stats` writes one row per pair (see `statsfile`).
"""

from __future__ import annotations

import gzip
from dataclasses import dataclass
from typing import TextIO

import numpy as np

from .matching import DataBatch, count_distinct_ngrams, match_ngrams, match_short_texts
from .records import Record, parse_record
from .ref_index import RefIndex
from .statsfile import HEADER, StatsRow

BATCH_BYTES = 4 << 20
"""Input bytes of the data file that are processed at once."""


@dataclass
class OverlapSummary:
    """Counts over the whole data file."""

    data_records: int = 0
    data_parse_failures: int = 0
    data_records_with_pairs: int = 0
    pairs: int = 0


def write_stats(data_path: str, index: RefIndex, output: TextIO) -> OverlapSummary:
    """Match the data file batch by batch and write the statistics file."""
    summary = OverlapSummary()
    output.write(HEADER)
    with gzip.open(data_path, "rb") as data_file:
        while lines := data_file.readlines(BATCH_BYTES):
            records = [parse_record(line) for line in lines]
            rows = _batch_rows(index, summary.data_records, records)
            output.writelines(row.to_line() for row in rows)

            summary.data_records += len(records)
            summary.data_parse_failures += records.count(None)
            summary.data_records_with_pairs += len({row.data_line for row in rows})
            summary.pairs += len(rows)
    return summary


def _batch_rows(index: RefIndex, first_line: int, records: list[Record | None]) -> list[StatsRow]:
    """The rows of one batch of consecutive data records (None = parse failure)."""
    batch = DataBatch(
        index,
        ((first_line + offset, record.texts) for offset, record in enumerate(records) if record),
    )
    ngram_matches = match_ngrams(index, batch)
    short_matches = match_short_texts(index, batch)

    # One row per pair that has either kind of match, in the order of the pair keys
    # (data line, then reference line).
    pair_keys = np.union1d(ngram_matches.pair_keys, short_matches.pair_keys)
    if not pair_keys.size:
        return []
    matched_ngrams, matched_short_texts = (
        np.zeros(pair_keys.size, dtype=np.int64) for _ in range(2)
    )
    matched_ngrams[np.searchsorted(pair_keys, ngram_matches.pair_keys)] = ngram_matches.counts
    matched_short_texts[np.searchsorted(pair_keys, short_matches.pair_keys)] = short_matches.counts

    data_lines, ref_lines = np.divmod(pair_keys, index.num_records)
    distinct_lines, row_to_line = np.unique(data_lines, return_inverse=True)
    data_ngrams = count_distinct_ngrams(index, batch, distinct_lines)[row_to_line]
    columns = (
        data_lines,
        ref_lines,
        matched_ngrams,
        index.record_ngram_counts[ref_lines],
        data_ngrams,
        matched_short_texts,
    )
    return [
        StatsRow(
            data_line,
            records[data_line - first_line].id,
            ref_line,
            index.record_ids[ref_line],
            *counts,
        )
        for data_line, ref_line, *counts in zip(*(c.tolist() for c in columns), strict=True)
    ]


def format_summary(summary: OverlapSummary, index: RefIndex) -> str:
    """The summary line: record counts of the data file and of the reference file."""
    fields = {
        "data_records": summary.data_records,
        "data_parse_failures": summary.data_parse_failures,
        "data_records_with_pairs": summary.data_records_with_pairs,
        "pairs": summary.pairs,
        "ref_records": index.num_records,
        "ref_parse_failures": index.parse_failures,
    }
    return " ".join(f"{name}={value}" for name, value in fields.items())
