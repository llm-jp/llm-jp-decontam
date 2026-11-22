"""Position-independent hashes of unit windows."""

from __future__ import annotations

import numpy as np

from .encoders import SEPARATOR

_SEED_BASE = 20261119


class RollingHash:
    """Polynomial hash of unit sequences modulo 2**64.

    The hash of the units u[0], ..., u[k-1] is the sum of value[u[i]] * base**i.  Equal
    sequences have equal hashes wherever they occur, so the hashes of all windows of an array
    are obtained from prefix sums.  A hash match is only a candidate: callers confirm every
    match by comparing the units.
    """

    def __init__(self, seed: int) -> None:
        rng = np.random.Generator(np.random.PCG64(_SEED_BASE + seed))
        max_value = np.iinfo(np.uint64).max
        self._unit_values = rng.integers(
            0, max_value, size=SEPARATOR + 1, dtype=np.uint64, endpoint=True
        )
        self._base = int(rng.integers(1 << 62, 1 << 63)) | 1
        self._inverse_base = pow(self._base, -1, 1 << 64)
        self._capacity = 0
        self._reserve(1 << 16)

    def _reserve(self, size: int) -> None:
        size = max(size, 2 * self._capacity)
        self._powers = self._power_table(self._base, size)
        self._inverse_powers = self._power_table(self._inverse_base, size)
        self._capacity = size

    @staticmethod
    def _power_table(base: int, size: int) -> np.ndarray:
        table = np.full(size, base, dtype=np.uint64)
        table[0] = 1
        return np.cumprod(table, dtype=np.uint64)

    def prefix_sums(self, units: np.ndarray) -> np.ndarray:
        """Return P with P[i] = sum of value[units[j]] * base**j over j < i."""
        size = units.size
        if size + 1 > self._capacity:
            self._reserve(size + 1)
        sums = np.empty(size + 1, dtype=np.uint64)
        sums[0] = 0
        np.cumsum(self._unit_values[units] * self._powers[:size], out=sums[1:])
        return sums

    def window_hashes(
        self, prefix_sums: np.ndarray, length: int, starts: np.ndarray | None = None
    ) -> np.ndarray:
        """Hashes of the windows of `length` units.

        With `starts`, the windows that begin at these positions; otherwise every window of
        the array, in order.
        """
        if starts is None:
            count = prefix_sums.size - length
            return (prefix_sums[length:] - prefix_sums[:count]) * self._inverse_powers[:count]
        window_sums = prefix_sums[starts + length] - prefix_sums[starts]
        return window_sums * self._inverse_powers[starts]
