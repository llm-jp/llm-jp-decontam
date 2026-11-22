"""Matching of a batch of data records against the reference index.

The results are keyed by pair: `pair_keys` holds data_line * index.num_records + ref_line,
sorted and distinct.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import NamedTuple

import numpy as np

from .arrays import lookup, ranges, sum_by_key, units_equal
from .encoded import EncodedTexts
from .ref_index import RefIndex

EXPAND_ROWS = 20_000_000
"""Upper bound of the (data record, reference record, n-gram) rows expanded at once."""


class NgramMatches(NamedTuple):
    """The pairs of a data record and a reference record that share an n-gram."""

    pair_keys: np.ndarray
    counts: np.ndarray
    """Number of distinct n-grams that occur in both records."""


class ShortTextMatches(NamedTuple):
    """The pairs where a short text of the reference record equals a whole text element of
    the data record."""

    pair_keys: np.ndarray
    counts: np.ndarray
    """Number of distinct short texts of the reference record that match."""


def _no_matches(result_type: type) -> tuple:
    return result_type(*(np.zeros(0, dtype=np.int64) for _ in result_type._fields))


class DataBatch(EncodedTexts):
    """The text elements of a batch of data records, converted like the reference."""

    def __init__(self, index: RefIndex, records: Iterable[tuple[int, list[str]]]) -> None:
        """`records` yields (line number, text elements) for every record of the batch."""
        texts = []
        lines = []
        for line_number, record_texts in records:
            texts.extend(record_texts)
            lines.extend([line_number] * len(record_texts))
        super().__init__(index.encode(texts)[1], lines)
        self.prefix_sums = index.hasher.prefix_sums(self.units)


def match_ngrams(index: RefIndex, batch: DataBatch) -> NgramMatches:
    """Count, for every pair of a data record and a reference record, their common n-grams."""
    n = index.ngram_length
    if batch.units.size < n or not index.ngram_hashes.size:
        return _no_matches(NgramMatches)

    # Windows of the data that equal an n-gram of the reference file.  A hash match is only a
    # candidate; it is confirmed by comparing the units.
    hashes = index.hasher.window_hashes(batch.prefix_sums, n)
    positions = index.candidate_windows(hashes)
    found, ngrams = lookup(index.ngram_hashes, hashes[positions])
    positions, ngrams = positions[found], ngrams[found]
    confirmed = units_equal(batch.units, positions, index.units, index.ngram_positions[ngrams], n)
    positions, ngrams = positions[confirmed], ngrams[confirmed]
    if not positions.size:
        return _no_matches(NgramMatches)

    # Distinct (data record, n-gram).
    num_ngrams = np.int64(index.ngram_hashes.size)
    data_lines = batch.owners[batch.text_at(positions)]
    data_lines, ngrams = np.divmod(np.unique(data_lines * num_ngrams + ngrams), num_ngrams)

    # Expand every n-gram to the reference records that hold it and count the n-grams per
    # (data record, reference record).
    num_refs = np.int64(index.num_records)
    sizes = index.ngram_record_counts[ngrams]
    pair_keys = []
    pair_counts = []
    for chunk in _chunks(sizes, EXPAND_ROWS):
        rows = ranges(index.ngram_record_offsets[ngrams[chunk]], sizes[chunk])
        keys = np.repeat(data_lines[chunk], sizes[chunk]) * num_refs + index.ngram_records[rows]
        keys, counts = np.unique(keys, return_counts=True)
        pair_keys.append(keys)
        pair_counts.append(counts)
    return NgramMatches(*sum_by_key(np.concatenate(pair_keys), np.concatenate(pair_counts)))


def _chunks(sizes: np.ndarray, max_total: int) -> Iterator[slice]:
    """Split the items into consecutive slices whose sizes add up to about `max_total`."""
    cumulative = np.cumsum(sizes)
    limits = np.arange(max_total, int(cumulative[-1]) + max_total, max_total)
    ends = np.unique(np.minimum(np.searchsorted(cumulative, limits) + 1, sizes.size))
    begin = 0
    for end in ends.tolist():
        yield slice(begin, end)
        begin = end


def match_short_texts(index: RefIndex, batch: DataBatch) -> ShortTextMatches:
    """Find the data text elements that equal a short text of a reference record."""
    num_refs = np.int64(index.num_records)
    matches = set()  # distinct (data line, short text)
    if index.short_texts:
        n = index.ngram_length
        for text in np.nonzero((batch.lengths > 0) & (batch.lengths < n))[0].tolist():
            start = int(batch.starts[text])
            key = batch.units[start : start + int(batch.lengths[text])].tobytes()
            if key in index.short_texts:
                matches.add((int(batch.owners[text]), key))
    pair_keys = [data_line * num_refs + index.short_texts[key] for data_line, key in matches]
    if not pair_keys:
        return _no_matches(ShortTextMatches)
    keys = np.concatenate(pair_keys)
    return ShortTextMatches(*sum_by_key(keys, np.ones(keys.size, dtype=np.int64)))


def count_distinct_ngrams(index: RefIndex, batch: DataBatch, data_lines: np.ndarray) -> np.ndarray:
    """Number of distinct n-grams of the data records at `data_lines` (sorted, distinct)."""
    n = index.ngram_length
    # Windows of the text elements of these records, sorted by record and hash.
    selected, slot_of_text = lookup(data_lines, batch.owners)
    positions, texts = batch.windows(n, selected)
    slots = slot_of_text[texts]
    hashes = index.hasher.window_hashes(batch.prefix_sums, n, positions)
    order = np.lexsort((hashes, slots))
    slots, hashes, positions = slots[order], hashes[order], positions[order]

    # A window repeats the previous one when record and hash are equal and the units agree
    # (equal hashes of different n-grams count as distinct).
    is_repeat = (slots[1:] == slots[:-1]) & (hashes[1:] == hashes[:-1])
    repeats = np.nonzero(is_repeat)[0]
    agree = units_equal(batch.units, positions[repeats], batch.units, positions[repeats + 1], n)
    is_repeat[repeats[~agree]] = False
    is_new = np.ones(slots.size, dtype=bool)
    is_new[1:] = ~is_repeat
    return np.bincount(slots[is_new], minlength=data_lines.size)
