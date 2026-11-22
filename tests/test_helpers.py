"""The shared helpers of llm_jp_decontam.core."""

import numpy as np
import pytest

from llm_jp_decontam.core.arrays import lookup, ranges, sum_by_key, units_equal
from llm_jp_decontam.core.encoded import EncodedTexts
from llm_jp_decontam.core.encoders import SEPARATOR
from llm_jp_decontam.core.errors import DecontamError
from llm_jp_decontam.core.outputs import replace_on_success, require_new


def test_ranges():
    assert ranges(np.array([5, 0, 9]), np.array([3, 0, 2])).tolist() == [5, 6, 7, 9, 10]
    assert ranges(np.array([], dtype=np.int64), np.array([], dtype=np.int64)).tolist() == []


def test_lookup():
    found, index = lookup(np.array([2, 5, 9]), np.array([5, 1, 9, 10]))
    assert found.tolist() == [True, False, True, False]
    assert index[found].tolist() == [1, 2]
    found, _ = lookup(np.array([], dtype=np.int64), np.array([1, 2]))
    assert found.tolist() == [False, False]


def test_sum_by_key():
    keys, sums = sum_by_key(np.array([7, 3, 7, 7]), np.array([1, 10, 2, 4]))
    assert keys.tolist() == [3, 7]
    assert sums.tolist() == [10, 7]


def test_units_equal():
    units = np.array([1, 2, 3, 1, 2, 4])
    equal = units_equal(units, np.array([0, 0]), units, np.array([3, 3]), 2)
    assert equal.tolist() == [True, True]
    assert units_equal(units, np.array([0]), units, np.array([3]), 3).tolist() == [False]


def test_encoded_texts_layout_and_windows():
    sequences = [
        np.array([1, 2, 3], dtype="<u4"),
        np.array([], dtype="<u4"),
        np.array([4, 5], dtype="<u4"),
    ]
    encoded = EncodedTexts(sequences, owners=[10, 10, 11])
    assert encoded.units.tolist() == [1, 2, 3, SEPARATOR, SEPARATOR, 4, 5]
    assert encoded.starts.tolist() == [0, 4, 5]
    assert encoded.text_at(np.array([0, 2, 5, 6])).tolist() == [0, 0, 2, 2]

    positions, texts = encoded.windows(2)
    assert positions.tolist() == [0, 1, 5]
    assert texts.tolist() == [0, 0, 2]
    positions, texts = encoded.windows(2, selected=np.array([False, True, True]))
    assert positions.tolist() == [5]
    assert EncodedTexts([], []).units.size == 0


def test_replace_on_success(tmp_path):
    target = tmp_path / "out.txt"
    with replace_on_success(str(target)) as temporary:
        with open(temporary, "w") as file:
            file.write("done")
        assert not target.exists()
    assert target.read_text() == "done"

    failed = tmp_path / "failed.txt"
    with pytest.raises(RuntimeError), replace_on_success(str(failed)) as temporary:
        with open(temporary, "w") as file:
            file.write("partial")
        raise RuntimeError
    assert not failed.exists()
    assert not (tmp_path / "failed.txt.tmp").exists()


def test_require_new(tmp_path):
    existing = tmp_path / "existing"
    existing.write_text("")
    require_new(str(tmp_path / "a"))
    with pytest.raises(DecontamError):
        require_new(str(existing))
