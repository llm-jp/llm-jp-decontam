import os
import random
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from reference import WORDS  # noqa: E402


@pytest.fixture(scope="session")
def spm_model(tmp_path_factory) -> str:
    """Path of the SentencePiece model used by the tests.

    The file named by the environment variable DECONTAM_TEST_SPM_MODEL when it is set (for
    example the LLM-jp-4 tokenizer model); otherwise a small unigram model trained here.
    """
    path = os.environ.get("DECONTAM_TEST_SPM_MODEL")
    if path:
        return path

    import sentencepiece

    directory = tmp_path_factory.mktemp("spm")
    rng = random.Random(0)
    sentences = [
        " ".join(rng.choice(WORDS) for _ in range(rng.randint(3, 12))) for _ in range(3000)
    ]
    corpus = directory / "corpus.txt"
    corpus.write_text("\n".join(sentences), encoding="utf-8")
    sentencepiece.SentencePieceTrainer.train(
        input=str(corpus),
        model_prefix=str(directory / "tiny"),
        vocab_size=120,
        model_type="unigram",
        hard_vocab_limit=False,
        character_coverage=1.0,
        minloglevel=2,
    )
    return str(directory / "tiny.model")
