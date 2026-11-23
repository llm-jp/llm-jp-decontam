"""Download the files of the evaluation datasets at fixed revisions into data/ref/<org>--<name>/."""
from huggingface_hub import snapshot_download

FILES = {
    "HuggingFaceH4/MATH-500": ("6e4ed1a2a79af7d8630a6b768ec859cb5af4d3be", ["test.jsonl"]),
    "HuggingFaceH4/aime_2024": ("2fe88a2f1091d5048c0f36abc874fb997b3dd99a", ["data/*"]),
    "yentinglin/aime_2025": ("6f71d77b0b89b9dabe07ab466c51df33f514df7f", ["data/*"]),
    "MathArena/aime_2026": ("d61f486805306e6e6b5913504c07763a99e1b112", ["data/*"]),
    "amphora/MCLM": ("aa789e49b04d5ca054c3a2a70d9bacd8a7499106", ["mt-math100.parquet"]),
    "Qwen/PolyMath": ("71e0db902e0ece05e208dfd8b1695bd3d95cf130", ["ja/*"]),
    "sbintuitions/JamC-QA": ("ec2f8a34b1cfb9dcd8c50583eb688ef2ee3fb671", ["v1.0/test-*"]),
    "tokyotech-llm/JEMHopQA": ("92d1f54bfe0fcf3c092e06d12ae52929a2548efe", ["v1.2/*"]),
    "nlp-waseda/JMMLU": ("3637b25e444ccfdcde4d23a783cbe8e674faa01b", ["JMMLU.zip"]),
    "tokyotech-llm/MMLU-ProX-Japanese": ("2048f94d16f2f211f3b28282bbda6a888cf887ab", ["*.parquet"]),
    "tokyotech-llm/MMLU-ProX-English": ("48715befa56941706abbd992dfdef617fcc05dc2", ["*.parquet"]),
    "livecodebench/code_generation_lite": ("0fe84c3912ea0c4d4a78037083943e8f0c4dd505", ["test6.jsonl", "code_generation_lite.py"]),
    "kogi-jwu/jhumaneval": ("35c54b74c11ec8f5699283c29e0d3ec9a94702ca", ["jhumaneval/*"]),
    "evalplus/humanevalplus": ("d32357cf319e50e9c8d8dab5ea876c72b0fd321b", ["data/*"]),
    "tokyotech-llm/M-IFEval-Ja": ("f42d9f0c9bd3e1be76b47c84143cd94d98eada8b", ["test.jsonl"]),
    "allenai/IFBench_test": ("ed7c12452594b7028b15807b86d3938150b663ae", ["data/*"]),
    "lighteval/sacrebleu_manual": ("3fbe6dac6f722b623516bbbf056dcf8d5939a75d", ["wmt20_en-ja/*", "wmt20_ja-en/*"]),
}
for repo, (rev, patterns) in FILES.items():
    path = snapshot_download(repo, repo_type="dataset", revision=rev, allow_patterns=patterns,
                             local_dir="data/ref/" + repo.replace("/", "--"))
    print(repo, rev, path, flush=True)
