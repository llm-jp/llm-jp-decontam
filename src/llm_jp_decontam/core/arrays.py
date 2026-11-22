"""Small numpy helpers shared by the index and the matching code."""

from __future__ import annotations

import numpy as np


def ranges(starts: np.ndarray, sizes: np.ndarray) -> np.ndarray:
    """Concatenation of arange(start, start + size) over all (start, size) pairs."""
    sizes = np.asarray(sizes, dtype=np.int64)
    first = np.cumsum(sizes) - sizes  # index of the first output element of every range
    shift = np.repeat(np.asarray(starts, dtype=np.int64) - first, sizes)
    return shift + np.arange(int(sizes.sum()), dtype=np.int64)


def lookup(sorted_values: np.ndarray, queries: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Search the queries in a sorted array of distinct values.

    Returns (found, index): `found` marks the queries that occur in `sorted_values`, and for
    these `index` is their position there.
    """
    index = np.searchsorted(sorted_values, queries)
    if not sorted_values.size:
        return np.zeros(queries.size, dtype=bool), index
    found = sorted_values[np.minimum(index, sorted_values.size - 1)] == queries
    return found, index


def sum_by_key(keys: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sum the values of equal keys.  Returns (sorted distinct keys, sums)."""
    distinct, inverse = np.unique(keys, return_inverse=True)
    sums = np.zeros(distinct.size, dtype=np.int64)
    np.add.at(sums, inverse, values)
    return distinct, sums


def units_equal(
    units_a: np.ndarray,
    positions_a: np.ndarray,
    units_b: np.ndarray,
    positions_b: np.ndarray,
    length: int,
) -> np.ndarray:
    """Compare runs of `length` units that begin at paired positions of two arrays.

    Returns a boolean mask with one entry per pair of positions.
    """
    equal = np.ones(positions_a.size, dtype=bool)
    for offset in range(length):
        equal &= units_a[positions_a + offset] == units_b[positions_b + offset]
    return equal
