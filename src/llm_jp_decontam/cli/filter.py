"""decontam-filter: remove the records of --data that satisfy a criterion on the statistics.

    decontam-filter --data <data.jsonl.gz> --stats <stats.tsv> --output <kept.jsonl.gz>
                    [--min-ref-coverage <number>] [--min-data-coverage <number>] [--short-texts]

A row of the statistics (a pair of a data record and a reference record) satisfies

    --min-ref-coverage X    when matched_ngrams / ref_ngrams >= X
    --min-data-coverage Y   when matched_ngrams / data_ngrams >= Y
    --short-texts           when matched_short_texts >= 1

A data record is removed when at least one row satisfies at least one of the given criteria.
At least one criterion is required.  X and Y are numbers in (0, 1].  --output receives the
kept lines of --data, unchanged and in the input order.
"""

from __future__ import annotations

import argparse
import sys

from ..core.errors import DecontamError
from ..core.filtering import Criteria, find_removals, split_data
from ..core.outputs import require_new


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="decontam-filter",
        description="Remove the records of --data that satisfy a criterion on the statistics "
        "of decontam-stats.",
    )
    parser.add_argument("--data", required=True, help="data file (.jsonl.gz)")
    parser.add_argument("--stats", required=True, help="output of decontam-stats for --data")
    parser.add_argument("--output", required=True, help="output file with the kept records")
    parser.add_argument(
        "--min-ref-coverage", type=float, help="remove when matched_ngrams / ref_ngrams >= X"
    )
    parser.add_argument(
        "--min-data-coverage", type=float, help="remove when matched_ngrams / data_ngrams >= Y"
    )
    parser.add_argument(
        "--short-texts", action="store_true", help="remove when matched_short_texts >= 1"
    )
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> None:
    criteria = Criteria(args.min_ref_coverage, args.min_data_coverage, args.short_texts)
    require_new(args.output)
    removals = find_removals(args.stats, criteria)
    num_lines = split_data(args.data, removals, args.output)
    kept = num_lines - len(removals)
    print(f"data_lines={num_lines} removed={len(removals)} kept={kept}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        run(args)
    except DecontamError as error:
        sys.exit(f"ERROR: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
