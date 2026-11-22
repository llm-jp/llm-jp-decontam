"""Direct implementation of the judgement of decontam-stats, and random test corpora.

The implementation uses Python sets of unit tuples and is written independently of the
package.  Units are code points for `char` and SentencePiece token ids for `spm`.
"""

from __future__ import annotations

import gzip
import json
import random
import re
import unicodedata
from collections.abc import Callable

Units = tuple[int, ...]
StatsRows = list[tuple]


def normalize(text: str, mode: str) -> str:
    if mode == "none":
        return text
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).lower())


def text_elements(record: dict) -> list[str]:
    texts = []
    for message in record["messages"]:
        texts.append(message["content"])
        if message.get("role") == "assistant" and isinstance(message.get("reasoning"), str):
            texts.append(message["reasoning"])
    return texts


def ngrams(sequences: list[Units], n: int) -> set[Units]:
    return {seq[i : i + n] for seq in sequences for i in range(len(seq) - n + 1)}


def expected_stats(
    data: list[dict], ref: list[dict], n: int, mode: str, to_units: Callable[[str], Units]
) -> StatsRows:
    """The rows that decontam-stats must write, as tuples in column order."""
    ref_entries = []
    for record in ref:
        texts = [normalize(text, mode) for text in text_elements(record)]
        sequences = [to_units(text) for text in texts]
        short_texts = {
            seq
            for text, seq in zip(texts, sequences, strict=True)
            if 0 < len(seq) < n and text.strip()
        }
        ref_entries.append((ngrams(sequences, n), short_texts))

    rows = []
    for data_line, record in enumerate(data):
        sequences = [to_units(normalize(text, mode)) for text in text_elements(record)]
        data_ngrams = ngrams(sequences, n)
        for ref_line, (ref_ngrams, short_texts) in enumerate(ref_entries):
            matched = len(ref_ngrams & data_ngrams)
            equal = sum(short in sequences for short in short_texts)
            if matched or equal:
                rows.append(
                    (
                        data_line,
                        record["id"],
                        ref_line,
                        ref[ref_line]["id"],
                        matched,
                        len(ref_ngrams),
                        len(data_ngrams),
                        equal,
                    )
                )
    return rows


def write_jsonl_gz(path, records: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_stats_file(path) -> tuple[list[str], StatsRows]:
    """Header and rows of a statistics file, parsed without the package."""
    with open(path, encoding="utf-8", newline="") as file:
        header = file.readline().rstrip("\n").split("\t")
        rows = []
        for line in file:
            cells = line.rstrip("\n").split("\t")
            rows.append((int(cells[0]), cells[1], int(cells[2]), cells[3], *map(int, cells[4:])))
    return header, rows


CHARS = ["a", "b", "c", "A", "B", " ", "  ", "\n", "x", "1", "２", "Ａ", "あ", "い", ".", "$"]
WORDS = [
    *["the", "answer", "is", "42", "Simplify", "$\\sqrt{50}$", "function", "return", "x", "+"],
    *["東京", "は", "日本の", "首都", "です。", "計算", "しなさい", "ＡＢＣ", "１２３"],
    *["Which", "of", "following", "statements", "true", "?", "(A)", "(B)", "Tokyo", "capital"],
    *["Japan", "1", ",", ".", "\n", "  ", "---", "=", "print(x)"],
]


def random_text(rng: random.Random, min_items: int, max_items: int, tokenizer: str) -> str:
    count = rng.randint(min_items, max_items)
    if tokenizer == "char":
        return "".join(rng.choice(CHARS) for _ in range(count))
    return "".join(rng.choice(WORDS) + rng.choice(["", " ", " ", "　"]) for _ in range(count))


def random_corpus(rng: random.Random, n: int, tokenizer: str) -> tuple[list[dict], list[dict]]:
    """Small random data and reference record lists that share texts through a common pool."""
    is_char = tokenizer == "char"
    pool = [random_text(rng, 0, n + 4 if is_char else n // 2 + 3, tokenizer) for _ in range(12)]

    def random_message() -> dict:
        choice = rng.random()
        if choice < 0.35:
            content = rng.choice(pool)
        elif choice < 0.8:
            content = random_text(rng, 0, 3 * n + 6 if is_char else n + 6, tokenizer)
        else:
            before = random_text(rng, 0, 3, tokenizer)
            after = random_text(rng, 0, 3, tokenizer)
            content = before + rng.choice(pool) + after
        message = {"role": rng.choice(["user", "assistant", "system"]), "content": content}
        if message["role"] == "assistant" and rng.random() < 0.5:
            if rng.random() < 0.4:
                message["reasoning"] = rng.choice(pool)
            else:
                message["reasoning"] = random_text(
                    rng, 0, 2 * n + 4 if is_char else n + 3, tokenizer
                )
        return message

    def random_records(prefix: str, count: int) -> list[dict]:
        return [
            {
                "id": f"{prefix}{i}",
                "messages": [random_message() for _ in range(rng.randint(1, 3))],
            }
            for i in range(count)
        ]

    ref = random_records("r", rng.randint(1, 14))
    data = random_records("d", rng.randint(1, 30))
    return data, ref
