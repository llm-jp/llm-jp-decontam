"""decontam-stats against the direct implementation (tests/reference.py) on random corpora."""

import random

import pytest
from reference import expected_stats, random_corpus, read_stats_file, write_jsonl_gz

from llm_jp_decontam.cli import stats
from llm_jp_decontam.core import overlap
from llm_jp_decontam.core.statsfile import COLUMNS

RUNS = 15
NGRAM_LENGTHS = [1, 2, 3, 4, 5, 6, 8, 12]
SMALL_BATCH_BYTES = 64  # many small batches of the data file


def unit_function(tokenizer: str, spm_model: str):
    if tokenizer == "char":
        return lambda text: tuple(ord(char) for char in text)
    import sentencepiece

    processor = sentencepiece.SentencePieceProcessor(model_file=spm_model)
    return lambda text: tuple(processor.encode(text))


@pytest.mark.parametrize("tokenizer", ["char", "spm"])
@pytest.mark.parametrize("seed", range(RUNS))
def test_identical_to_reference(tmp_path, monkeypatch, spm_model, tokenizer, seed):
    rng = random.Random(f"stats-{tokenizer}-{seed}")
    n = rng.choice(NGRAM_LENGTHS)
    data, ref = random_corpus(rng, n, tokenizer)
    data_path = tmp_path / "data.jsonl.gz"
    ref_path = tmp_path / "ref.jsonl.gz"
    write_jsonl_gz(data_path, data)
    write_jsonl_gz(ref_path, ref)
    to_units = unit_function(tokenizer, spm_model)
    model_args = ["--tokenizer-model", spm_model] if tokenizer == "spm" else []
    default_batch_bytes = overlap.BATCH_BYTES

    for mode in ("none", "nfkc-lower-ws"):
        expected = expected_stats(data, ref, n, mode, to_units)
        for batch_bytes in (default_batch_bytes, SMALL_BATCH_BYTES):
            monkeypatch.setattr(overlap, "BATCH_BYTES", batch_bytes)
            output = tmp_path / f"stats_{mode}_{batch_bytes}.tsv"
            args = ["--data", str(data_path), "--ref", str(ref_path), "--output", str(output)]
            args += ["--ngram-size", str(n), "--normalize", mode, "--tokenizer", tokenizer]
            assert stats.main(args + model_args) == 0
            header, rows = read_stats_file(output)
            assert tuple(header) == COLUMNS
            assert rows == expected


def test_some_corpora_have_every_kind_of_match(tmp_path):
    """The random corpora must exercise n-gram matches and short-text matches."""
    totals = {"matched_ngrams": 0, "matched_short_texts": 0}
    for seed in range(RUNS):
        rng = random.Random(f"stats-char-{seed}")
        n = rng.choice(NGRAM_LENGTHS)
        data, ref = random_corpus(rng, n, "char")
        to_units = unit_function("char", "")
        for row in expected_stats(data, ref, n, "nfkc-lower-ws", to_units):
            totals["matched_ngrams"] += row[4]
            totals["matched_short_texts"] += row[7]
    assert all(total > 0 for total in totals.values()), totals


@pytest.mark.parametrize(
    "extra_args",
    [
        ["--tokenizer", "spm"],
        ["--tokenizer", "char", "--tokenizer-model", "model"],
        ["--tokenizer", "char", "--ngram-size", "0"],
    ],
)
def test_argument_errors(tmp_path, extra_args):
    args = ["--data", "x", "--ref", "y", "--output", str(tmp_path / "out.tsv")]
    args += ["--ngram-size", "5", "--normalize", "none"]
    with pytest.raises(SystemExit) as error:
        stats.main(args + extra_args)
    assert error.value.code not in (0, None)
