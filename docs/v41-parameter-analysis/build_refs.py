"""Build the --ref files from data/ref/: one record per evaluation item, the text shown to the model
(question, and the options of multiple-choice tasks, joined by newlines). Answers are not included.
Outputs work/ref/<benchmark>.jsonl.gz and work/ref/all.jsonl.gz (id = "<benchmark>:<item>")."""
import ast, csv, glob, gzip, io, json, os, zipfile
import pyarrow.parquet as pq

R = "data/ref/"


def rows_parquet(pattern):
    for path in sorted(glob.glob(R + pattern)):
        yield from pq.read_table(path).to_pylist()


def rows_jsonl(path):
    with open(R + path, encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def as_dict(t):
    """The translation column is a string holding a Python dict (read as swallow-evaluation-instruct does)."""
    d = ast.literal_eval(t) if isinstance(t, str) else t
    return {k: (v[0] if isinstance(v, list) else v) for k, v in d.items()}


# Not used by swallow-evaluation-instruct (CC BY-NC-ND subjects).
JMMLU_EXCLUDED = {"japanese_civics", "japanese_idiom", "japanese_geography"}


def jmmlu():
    with zipfile.ZipFile(R + "nlp-waseda--JMMLU/JMMLU.zip") as z:
        for name in sorted(n for n in z.namelist() if n.startswith("JMMLU/test/") and n.endswith(".csv")
                           and os.path.basename(n)[:-4] not in JMMLU_EXCLUDED):
            text = z.read(name).decode("utf-8-sig")
            for i, r in enumerate(csv.DictReader(io.StringIO(text))):
                yield f"{os.path.basename(name)[:-4]}-{i}", [r["question"], r["A"], r["B"], r["C"], r["D"]]


def mmlu_prox(lang):
    for r in rows_parquet(f"tokyotech-llm--MMLU-ProX-{lang}/*.parquet"):
        opts = [r[f"option_{k}"] for k in range(10) if r.get(f"option_{k}") not in (None, "", "N/A")]
        yield r["question_id"], [r["question"], *opts]


def items():
    yield "math500", ((r["unique_id"], [r["problem"]]) for r in rows_jsonl("HuggingFaceH4--MATH-500/test.jsonl"))
    yield "aime2024", ((r["id"], [r["problem"]]) for r in rows_parquet("HuggingFaceH4--aime_2024/data/*.parquet"))
    yield "aime2025", ((r["id"], [r["problem"]]) for r in rows_parquet("yentinglin--aime_2025/data/*.parquet"))
    yield "aime2026", ((r["problem_idx"], [r["problem"]]) for r in rows_parquet("MathArena--aime_2026/data/*.parquet"))
    yield "mclm_math100_ja", ((i, [r["ja"]]) for i, r in enumerate(rows_parquet("amphora--MCLM/mt-math100.parquet")))
    for level in ("high", "top"):
        yield f"polymath_ja_{level}", ((r["id"], [r["question"]]) for r in rows_parquet(f"Qwen--PolyMath/ja/{level}.parquet"))
    yield "jamcqa", ((r["qid"], [r["question"], *(r[f"choice{k}"] for k in range(4))])
                     for r in rows_parquet("sbintuitions--JamC-QA/v1.0/test-*.parquet"))
    yield "jemhopqa", ((r["qid"], [r["question"]]) for r in rows_parquet("tokyotech-llm--JEMHopQA/v1.2/validation-*.parquet"))
    yield "jmmlu", jmmlu()
    yield "mmluprox_ja", mmlu_prox("Japanese")
    yield "mmluprox_en", mmlu_prox("English")
    yield "lcb_v6", ((r["question_id"], [r["question_content"]]) for r in rows_jsonl("livecodebench--code_generation_lite/test6.jsonl"))
    yield "jhumaneval", ((r["task_id"], [r["prompt"]]) for r in rows_parquet("kogi-jwu--jhumaneval/jhumaneval/*.parquet"))
    yield "humanevalplus", ((r["task_id"], [r["prompt"]]) for r in rows_parquet("evalplus--humanevalplus/data/*.parquet"))
    yield "mifeval_ja", ((r["key"], [r["prompt"]]) for r in rows_jsonl("tokyotech-llm--M-IFEval-Ja/test.jsonl"))
    yield "ifbench", ((r["key"], [r["prompt"]]) for r in rows_parquet("allenai--IFBench_test/data/*.parquet"))
    for src, dst in (("en", "ja"), ("ja", "en")):
        yield f"wmt20_{src}_{dst}", ((i, [as_dict(r["translation"])[src]])
                                    for i, r in enumerate(rows_parquet(f"lighteval--sacrebleu_manual/wmt20_{src}-{dst}/*.parquet")))


os.makedirs("work/ref", exist_ok=True)
assert not os.path.exists("work/ref/all.jsonl.gz")
with gzip.open("work/ref/all.jsonl.gz", "wt", encoding="utf-8") as all_out:
    for bench, its in items():
        n = 0
        with gzip.open(f"work/ref/{bench}.jsonl.gz", "wt", encoding="utf-8") as out:
            for item_id, parts in its:
                text = "\n".join(p for p in parts if isinstance(p, str) and p)
                line = json.dumps({"id": f"{bench}:{item_id}", "messages": [{"role": "user", "content": text}]}, ensure_ascii=False) + "\n"
                out.write(line)
                all_out.write(line)
                n += 1
        print(f"{bench}\t{n}")
