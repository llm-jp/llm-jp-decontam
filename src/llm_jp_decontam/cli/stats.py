"""decontam-stats: overlap statistics between the records of --data and the records of --ref.

    decontam-stats --data <data.jsonl.gz> --ref <ref.jsonl.gz> --output <stats.tsv>
                   --ngram-size <int> --normalize <none|nfkc-lower-ws>
                   --tokenizer <char|spm> [--tokenizer-model <sentencepiece .model>]

Every text element (the `content` or the `reasoning` of one message) is normalized
(--normalize) and turned into units (--tokenizer): Unicode code points for `char`,
SentencePiece tokens for `spm`.  An n-gram is a run of --ngram-size units inside one text element.

The output has one row per pair of a data record and a reference record that share an n-gram,
or where a reference text element shorter than --ngram-size units equals a whole data text element
(columns: llm_jp_decontam.core.statsfile).  A summary line goes to the standard error output.
"""

from __future__ import annotations

import argparse
import os
import sys

# One thread per process: parallelism is left to the caller.  Set before numpy is imported.
for _variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_variable, "1")

from ..core.encoders import make_encoder  # noqa: E402
from ..core.errors import DecontamError  # noqa: E402
from ..core.normalize import NORMALIZERS  # noqa: E402
from ..core.outputs import replace_on_success, require_new  # noqa: E402
from ..core.overlap import format_summary, write_stats  # noqa: E402
from ..core.ref_index import RefIndex  # noqa: E402


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="decontam-stats",
        description="Overlap statistics: list the pairs (data record, ref record) that share an "
        "n-gram, or where a short text of the ref record equals a text of the data record.",
    )
    parser.add_argument("--data", required=True, help="data file (.jsonl.gz)")
    parser.add_argument(
        "--ref", required=True, help="reference file (.jsonl.gz, same format as --data)"
    )
    parser.add_argument(
        "--output", required=True, help="output file (statistics TSV, the input of decontam-filter)"
    )
    parser.add_argument(
        "--ngram-size",
        required=True,
        type=int,
        help="n-gram length in units of --tokenizer (code points or tokens)",
    )
    parser.add_argument(
        "--normalize", required=True, choices=sorted(NORMALIZERS), help="normalization of the text"
    )
    parser.add_argument(
        "--tokenizer",
        required=True,
        choices=["char", "spm"],
        help="unit of the n-grams: char = Unicode code point, spm = SentencePiece token",
    )
    parser.add_argument(
        "--tokenizer-model", help="SentencePiece model file (required for --tokenizer spm)"
    )
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> None:
    require_new(args.output)
    encoder = make_encoder(args.tokenizer, args.tokenizer_model)
    index = RefIndex(args.ref, args.ngram_size, NORMALIZERS[args.normalize], encoder)
    with (
        replace_on_success(args.output) as temporary,
        open(temporary, "w", encoding="utf-8", newline="") as output,
    ):
        summary = write_stats(args.data, index, output)
    print(format_summary(summary, index), file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        run(args)
    except DecontamError as error:
        sys.exit(f"ERROR: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
