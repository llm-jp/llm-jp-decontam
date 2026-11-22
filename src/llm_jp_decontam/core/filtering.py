"""Removal of data records by criteria on the overlap statistics.

A data record is removed when at least one row of the statistics (a pair of the data record and
a reference record) satisfies at least one of the given criteria (see `Criteria`).
"""

from __future__ import annotations

import gzip
from dataclasses import dataclass

from .errors import DecontamError
from .outputs import replace_on_success
from .records import parse_record
from .statsfile import StatsRow, read_stats


@dataclass(frozen=True)
class Criteria:
    """The removal criteria.  A criterion that is None or False is not applied.

    min_ref_coverage     matched_ngrams / ref_ngrams >= this value, in (0, 1]
    min_data_coverage    matched_ngrams / data_ngrams >= this value, in (0, 1]
    short_texts          matched_short_texts >= 1
    """

    min_ref_coverage: float | None = None
    min_data_coverage: float | None = None
    short_texts: bool = False

    def __post_init__(self) -> None:
        if (
            self.min_ref_coverage is None
            and self.min_data_coverage is None
            and not self.short_texts
        ):
            raise DecontamError("at least one criterion is required")
        for coverage in (self.min_ref_coverage, self.min_data_coverage):
            if coverage is not None and not 0 < coverage <= 1:
                raise DecontamError(f"a coverage threshold must be in (0, 1]: {coverage}")

    def satisfied_by(self, row: StatsRow) -> bool:
        return (
            (
                self.min_ref_coverage is not None
                and row.ref_ngrams > 0
                and row.matched_ngrams >= self.min_ref_coverage * row.ref_ngrams
            )
            or (
                self.min_data_coverage is not None
                and row.data_ngrams > 0
                and row.matched_ngrams >= self.min_data_coverage * row.data_ngrams
            )
            or (self.short_texts and row.matched_short_texts >= 1)
        )


def find_removals(stats_path: str, criteria: Criteria) -> dict[int, str]:
    """The data records to remove: data line -> data id."""
    removals: dict[int, str] = {}
    for row in read_stats(stats_path):
        if criteria.satisfied_by(row):
            removals[row.data_line] = row.data_id
    return removals


def split_data(data_path: str, removals: dict[int, str], kept_path: str) -> int:
    """Copy the lines of the data file that are not removed, unchanged, to `kept_path`.

    The id of every removed record is compared with the id in the statistics; a difference
    means that the statistics belong to another file.  Returns the number of lines.
    """
    with (
        replace_on_success(kept_path) as temporary,
        gzip.open(temporary, "wb") as kept,
        gzip.open(data_path, "rb") as data_file,
    ):
        num_lines = 0
        for data_line, line in enumerate(data_file):
            num_lines += 1
            data_id = removals.get(data_line)
            if data_id is None:
                kept.write(line)
                continue
            record = parse_record(line)
            if record is None or record.id != data_id:
                raise DecontamError(
                    f"the statistics do not belong to the data file (line {data_line})"
                )
        if removals and max(removals) >= num_lines:
            raise DecontamError(
                f"the statistics do not belong to the data file (line {max(removals)})"
            )
    return num_lines
