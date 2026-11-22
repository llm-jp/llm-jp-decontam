"""Index of the n-grams and the short texts of the reference records."""

from __future__ import annotations

import gzip

import numpy as np

from .arrays import units_equal
from .encoded import EncodedTexts
from .encoders import Encoder
from .errors import DecontamError
from .hashing import RollingHash
from .normalize import Normalizer
from .records import parse_record

_MAX_HASH_SEEDS = 8
_COLLISION_CHECK_CHUNK = 1 << 16
_BITMAP_BUILD_CHUNK = 1 << 15


class RefIndex:
    """The n-grams and the short texts of all records of a reference file.

    A text element with at least `ngram_length` units contributes its n-grams.  A shorter text
    element with at least one unit and one non-whitespace character is a short text; a data
    text element equal to it is a match (`short_texts`: units as bytes -> reference records).
    The index
    also owns the normalization and the encoder, so that the data is converted to units in
    exactly the same way as the reference (`encode`).

    N-gram index (one entry per distinct n-gram, sorted by hash):
        ngram_hashes           hash of the n-gram
        ngram_positions        one position of the n-gram in `units`
        ngram_record_counts    number of reference records that hold the n-gram
        ngram_record_offsets   start of the records of the n-gram in `ngram_records`
        ngram_records          reference records, grouped by n-gram
    Per reference record (indexed by line number):
        record_ids, record_ngram_counts
    """

    def __init__(
        self, path: str, ngram_length: int, normalize: Normalizer, encoder: Encoder
    ) -> None:
        if ngram_length < 1:
            raise DecontamError("the n-gram length must be 1 or more")
        self.ngram_length = ngram_length
        self._normalize = normalize
        self._encoder = encoder
        self.record_ids: list[str] = []
        self.parse_failures = 0

        long_texts, short_text_records = self._read(path)
        self.short_texts = {
            key: np.array(sorted(records), dtype=np.int64)
            for key, records in short_text_records.items()
        }
        self._index_ngrams(long_texts)
        self._build_bitmap()

    @property
    def num_records(self) -> int:
        return len(self.record_ids)

    def encode(self, texts: list[str]) -> tuple[list[str], list[np.ndarray]]:
        """Normalize the texts and convert them to units.  Returns both forms."""
        normalized = [self._normalize(text) for text in texts]
        return normalized, self._encoder.encode_many(normalized)

    def _read(self, path: str) -> tuple[EncodedTexts, dict[bytes, set[int]]]:
        """Read the file.  Returns the text elements that have n-grams, and for every short
        text (as the bytes of its units) the records that hold it."""
        sequences: list[np.ndarray] = []
        owners: list[int] = []
        short_text_records: dict[bytes, set[int]] = {}
        with gzip.open(path, "rb") as file:
            for line in file:
                record = parse_record(line)
                if record is None:
                    self.parse_failures += 1
                    self.record_ids.append("")
                    continue
                record_line = len(self.record_ids)
                self.record_ids.append(record.id)
                for text, units in zip(*self.encode(record.texts), strict=True):
                    if units.size >= self.ngram_length:
                        sequences.append(units)
                        owners.append(record_line)
                    elif units.size and text.strip():
                        short_text_records.setdefault(units.tobytes(), set()).add(record_line)
        return EncodedTexts(sequences, owners), short_text_records

    def _index_ngrams(self, long_texts: EncodedTexts) -> None:
        n = self.ngram_length
        self.units = long_texts.units
        positions, texts = long_texts.windows(n)
        records = long_texts.owners[texts]

        # Sort the windows by hash.  The sort is stable and the windows are ordered by record,
        # so equal n-grams stay ordered by record.  A seed is accepted when no two different
        # n-grams share a hash.
        for seed in range(_MAX_HASH_SEEDS):
            self.hasher = RollingHash(seed)
            hashes = self.hasher.window_hashes(self.hasher.prefix_sums(self.units), n, positions)
            order = np.argsort(hashes, kind="stable")
            if self._equal_hashes_are_equal_ngrams(hashes[order], positions[order]):
                break
        else:
            raise DecontamError(
                "two different n-grams of --ref share a 64-bit hash with every seed"
            )
        hashes, positions, records = hashes[order], positions[order], records[order]

        is_new_ngram = np.ones(hashes.size, dtype=bool)
        is_new_ngram[1:] = hashes[1:] != hashes[:-1]
        is_new_pair = is_new_ngram.copy()  # distinct (n-gram, record)
        is_new_pair[1:] |= records[1:] != records[:-1]

        self.ngram_hashes = hashes[is_new_ngram]
        self.ngram_positions = positions[is_new_ngram]
        ngram_of_pair = (np.cumsum(is_new_ngram) - 1)[is_new_pair]
        self.ngram_records = records[is_new_pair]
        self.ngram_record_counts = np.bincount(ngram_of_pair, minlength=self.ngram_hashes.size)
        self.ngram_record_offsets = np.cumsum(self.ngram_record_counts) - self.ngram_record_counts
        self.record_ngram_counts = np.bincount(self.ngram_records, minlength=self.num_records)

    def _equal_hashes_are_equal_ngrams(self, hashes: np.ndarray, positions: np.ndarray) -> bool:
        """Check that windows with equal hashes hold equal units (hashes sorted)."""
        same_as_next = np.nonzero(hashes[1:] == hashes[:-1])[0]
        for begin in range(0, same_as_next.size, _COLLISION_CHECK_CHUNK):
            chunk = same_as_next[begin : begin + _COLLISION_CHECK_CHUNK]
            equal = units_equal(
                self.units, positions[chunk], self.units, positions[chunk + 1], self.ngram_length
            )
            if not equal.all():
                return False
        return True

    def _build_bitmap(self) -> None:
        """Build a bitmap over the top bits of the n-gram hashes.

        It rejects most windows of the data that match no n-gram before the binary search.
        """
        size_bits = np.ceil(np.log2(max(1, self.ngram_hashes.size) * 32))
        self._bitmap_bits = int(min(32, max(16, size_bits)))
        self._bitmap = np.zeros(1 << (self._bitmap_bits - 3), dtype=np.uint8)
        for begin in range(0, self.ngram_hashes.size, _BITMAP_BUILD_CHUNK):
            byte_index, bit_mask = self._bitmap_slots(
                self.ngram_hashes[begin : begin + _BITMAP_BUILD_CHUNK]
            )
            np.bitwise_or.at(self._bitmap, byte_index, bit_mask)

    def _bitmap_slots(self, hashes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        top_bits = hashes >> np.uint64(64 - self._bitmap_bits)
        byte_index = (top_bits >> np.uint64(3)).astype(np.intp)
        bit_mask = np.uint8(1) << (top_bits & np.uint64(7)).astype(np.uint8)
        return byte_index, bit_mask

    def candidate_windows(self, hashes: np.ndarray) -> np.ndarray:
        """Indices of the hashes that may be n-grams of the reference file."""
        byte_index, bit_mask = self._bitmap_slots(hashes)
        return np.nonzero(self._bitmap[byte_index] & bit_mask)[0]
