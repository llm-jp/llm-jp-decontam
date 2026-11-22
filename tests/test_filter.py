"""decontam-filter against a direct implementation of its criteria."""

import gzip
import random

import pytest
from reference import random_corpus, read_stats_file, write_jsonl_gz

from llm_jp_decontam.cli import filter as decontam_filter
from llm_jp_decontam.cli import stats

SETTINGS = [
    {"--min-ref-coverage": "0.5"},
    {"--min-ref-coverage": "1.0"},
    {"--min-data-coverage": "0.25"},
    {"--min-data-coverage": "0.9"},
    {"--short-texts": None},
    {"--min-ref-coverage": "0.5", "--min-data-coverage": "0.5", "--short-texts": None},
]


def satisfied(row: tuple, setting: dict) -> bool:
    matched, ref_ngrams, data_ngrams, short_texts = row[4:8]
    min_ref = setting.get("--min-ref-coverage")
    min_data = setting.get("--min-data-coverage")
    return (
        (min_ref is not None and ref_ngrams > 0 and matched >= float(min_ref) * ref_ngrams)
        or (min_data is not None and data_ngrams > 0 and matched >= float(min_data) * data_ngrams)
        or ("--short-texts" in setting and short_texts >= 1)
    )


def run_stats(data_path, ref_path, output, n: int) -> None:
    args = ["--data", str(data_path), "--ref", str(ref_path), "--output", str(output)]
    args += ["--ngram-size", str(n), "--normalize", "nfkc-lower-ws", "--tokenizer", "char"]
    assert stats.main(args) == 0


def read_gz_lines(path) -> list[bytes]:
    with gzip.open(path, "rb") as file:
        return file.read().splitlines(keepends=True)


@pytest.mark.parametrize("seed", range(8))
def test_identical_to_reference(tmp_path, seed):
    rng = random.Random(f"filter-{seed}")
    n = rng.choice([2, 3, 4, 6])
    data, ref = random_corpus(rng, n, "char")
    data_path, ref_path, stats_path = (
        tmp_path / name for name in ("d.jsonl.gz", "r.jsonl.gz", "s.tsv")
    )
    write_jsonl_gz(data_path, data)
    write_jsonl_gz(ref_path, ref)
    run_stats(data_path, ref_path, stats_path, n)
    rows = read_stats_file(stats_path)[1]
    data_lines = read_gz_lines(data_path)

    for number, setting in enumerate(SETTINGS):
        removed = {row[0] for row in rows if satisfied(row, setting)}
        kept = tmp_path / f"kept{number}.jsonl.gz"
        args = ["--data", str(data_path), "--stats", str(stats_path), "--output", str(kept)]
        for option, value in setting.items():
            args += [option] if value is None else [option, value]
        assert decontam_filter.main(args) == 0
        assert read_gz_lines(kept) == [
            line for i, line in enumerate(data_lines) if i not in removed
        ]


@pytest.fixture
def small_case(tmp_path):
    """Two data records; the first one equals the only reference record."""
    data = [
        {"id": "d0", "messages": [{"role": "user", "content": "abcdefgh"}]},
        {"id": "d1", "messages": [{"role": "user", "content": "zzzz"}]},
    ]
    ref = [{"id": "r0", "messages": [{"role": "user", "content": "abcdefgh"}]}]
    data_path, ref_path, stats_path = (
        tmp_path / name for name in ("d.jsonl.gz", "r.jsonl.gz", "s.tsv")
    )
    write_jsonl_gz(data_path, data)
    write_jsonl_gz(ref_path, ref)
    run_stats(data_path, ref_path, stats_path, 4)
    return data, data_path, stats_path


@pytest.mark.parametrize(
    "criteria_args",
    [
        [],
        ["--min-ref-coverage", "1.5"],
    ],
)
def test_argument_errors(tmp_path, small_case, criteria_args):
    _, data_path, stats_path = small_case
    kept = tmp_path / "kept.jsonl.gz"
    args = ["--data", str(data_path), "--stats", str(stats_path), "--output", str(kept)]
    with pytest.raises(SystemExit) as error:
        decontam_filter.main(args + criteria_args)
    assert error.value.code not in (0, None)
    assert not kept.exists()


def test_statistics_of_another_data_file(tmp_path, small_case):
    data, _, stats_path = small_case
    other_path = tmp_path / "other.jsonl.gz"
    write_jsonl_gz(other_path, list(reversed(data)))
    kept = tmp_path / "kept.jsonl.gz"
    args = ["--data", str(other_path), "--stats", str(stats_path), "--output", str(kept)]
    with pytest.raises(SystemExit) as error:
        decontam_filter.main(args + ["--min-ref-coverage", "1.0"])
    assert error.value.code not in (0, None)
    assert not kept.exists()
    assert not (tmp_path / "kept.jsonl.gz.tmp").exists()
